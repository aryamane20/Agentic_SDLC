"""Generate and fetch PM reports via PMAgent (Project 1 core)."""

import time
import uuid
from functools import lru_cache
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from agent.main import PMAgent
from agent.validator import SchemaValidator, sync_pm_confidence_metadata_mirrors

from backend.api.db import store
from backend.api.deps import planr_user_id
from backend.api.models.gate import GateState, GenerateReportRequest
from backend.api.models.session import ReportEntry, SessionState
from backend.api.services.approval_gate import evaluate_gate
from backend.api.services.input_guard import classify_input

router = APIRouter()
_validator = SchemaValidator()

_MAX_DOC_BYTES = 5 * 1024 * 1024
_MAX_EXTRACT_CHARS = 120_000
_MAX_VALIDATION_ATTEMPTS = 3


def _compose_brief_for_agent(brief: str, prd_text: Optional[str]) -> str:
    parts: list[str] = []
    b = (brief or "").strip()
    p = (prd_text or "").strip()
    if b:
        parts.append(b)
    if p:
        parts.append("--- ATTACHED PRD ---\n" + p)
    return "\n\n".join(parts)


@lru_cache(maxsize=8)
def _agent_for_version(prompt_version: str) -> PMAgent:
    return PMAgent(prompt_version=prompt_version)


@router.post("/extract-document")
async def extract_document(file: UploadFile = File(...)) -> dict:
    """Pull plain text from a PRD upload (.txt, .md, .pdf, .docx)."""
    try:
        from docx import Document  # type: ignore[import-untyped]
    except ImportError:
        Document = None  # type: ignore[assignment,misc]
    try:
        from pypdf import PdfReader  # type: ignore[import-untyped]
    except ImportError:
        PdfReader = None  # type: ignore[assignment,misc]

    raw = await file.read()
    if len(raw) > _MAX_DOC_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {_MAX_DOC_BYTES // (1024 * 1024)} MB)",
        )
    name = (file.filename or "upload").lower()
    text = ""

    if name.endswith((".txt", ".md", ".markdown")) or (
        file.content_type and file.content_type.startswith("text/")
    ):
        text = raw.decode("utf-8", errors="replace")
    elif name.endswith(".pdf"):
        if PdfReader is None:
            raise HTTPException(
                status_code=501,
                detail="PDF extraction unavailable (install pypdf)",
            )
        reader = PdfReader(BytesIO(raw))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    elif name.endswith(".docx"):
        if Document is None:
            raise HTTPException(
                status_code=501,
                detail="DOCX extraction unavailable (install python-docx)",
            )
        doc = Document(BytesIO(raw))
        text = "\n".join(p.text for p in doc.paragraphs if p.text)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Use .txt, .md, .pdf, or .docx",
        )

    text = text.strip()
    if len(text) > _MAX_EXTRACT_CHARS:
        text = text[:_MAX_EXTRACT_CHARS]
    if not text:
        raise HTTPException(
            status_code=422,
            detail="No extractable text in document",
        )
    return {"text": text, "filename": file.filename or "upload"}


@router.post("/generate")
def generate_report(
    body: GenerateReportRequest,
    user_id: str = Depends(planr_user_id),
) -> dict:
    state = store.load_session(user_id, body.session_id)
    if state is None:
        state = SessionState(session_id=body.session_id)

    composed = _compose_brief_for_agent(body.brief, body.prd_text)

    verdict = classify_input(composed, prd_text=body.prd_text or "")
    if verdict.verdict != "OK":
        code = "input_refused" if verdict.verdict == "REFUSED" else "brief_missing"
        raise HTTPException(status_code=422, detail={
            "code": code,
            "reason": verdict.reason_code,
            "message": verdict.user_message,
        })

    agent = _agent_for_version(body.prompt_version or "v1.6.2")
    run: dict | None = None
    validation: dict | None = None
    report: dict | None = None
    for attempt in range(_MAX_VALIDATION_ATTEMPTS):
        use_cache = body.use_cache if attempt == 0 else False
        run = agent.run(
            composed,
            input_source=f"backend-session-{body.session_id}",
            use_cache=use_cache,
        )
        report = run.get("report")
        if not isinstance(report, dict):
            raise HTTPException(
                status_code=502,
                detail="Agent returned no report dict — parse or model error",
            )

        sync_pm_confidence_metadata_mirrors(report)
        validation = _validator.validate(dict(report))
        # Second enforcement after validate(): Pydantic/normalize may expose breakdown fields that
        # bump the displayed score; caps must match gate evaluation on the final dict.
        agent._enforce_hard_caps(report)
        sync_pm_confidence_metadata_mirrors(report)
        if validation.get("valid"):
            break
        if attempt + 1 < _MAX_VALIDATION_ATTEMPTS:
            time.sleep(1.0 * (attempt + 1))

    assert run is not None and report is not None and validation is not None
    gate = evaluate_gate(report)

    rid = f"rpt_{uuid.uuid4().hex[:12]}"
    entry = ReportEntry(
        report_id=rid,
        brief=composed,
        report=report,
        gate=gate,
        input_tokens=run.get("input_tokens"),
        output_tokens=run.get("output_tokens"),
        tokens_used=run.get("tokens_used"),
    )
    state.reports.append(entry)
    store.save_session(user_id, state)

    return {
        "session_id": body.session_id,
        "report_id": rid,
        "report_revision": entry.report_revision,
        "report": report,
        "gate": gate.model_dump(mode="json"),
        "validation": validation,
        "tokens_used": run.get("tokens_used"),
        "input_tokens": run.get("input_tokens"),
        "output_tokens": run.get("output_tokens"),
        "cache_hit": run.get("cache_hit", False),
    }


@router.get("/{report_id}")
def get_report(
    report_id: str,
    user_id: str = Depends(planr_user_id),
) -> dict:
    found = store.find_report_session(user_id, report_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Report not found")
    session_id, index = found
    state = store.load_session(user_id, session_id)
    assert state is not None
    entry = state.reports[index]
    return {
        "session_id": session_id,
        "report_id": entry.report_id,
        "report_revision": entry.report_revision,
        "brief": entry.brief,
        "report": entry.report,
        "gate": entry.gate.model_dump(mode="json"),
        "refinements": [r.model_dump(mode="json") for r in entry.refinements],
    }
