"""Generate and fetch PM reports via PMAgent (Project 1 core)."""

import uuid
from functools import lru_cache

from fastapi import APIRouter, HTTPException

from agent.main import PMAgent
from agent.validator import SchemaValidator

from backend.api.db import store
from backend.api.models.gate import GateState, GenerateReportRequest
from backend.api.models.session import ReportEntry
from backend.api.services.approval_gate import evaluate_gate

router = APIRouter()
_validator = SchemaValidator()


@lru_cache(maxsize=8)
def _agent_for_version(prompt_version: str) -> PMAgent:
    return PMAgent(prompt_version=prompt_version)


@router.post("/generate")
def generate_report(body: GenerateReportRequest) -> dict:
    state = store.load_session(body.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")

    agent = _agent_for_version(body.prompt_version or "v1.6.1")
    run = agent.run(
        body.brief,
        input_source=f"backend-session-{body.session_id}",
        use_cache=body.use_cache,
    )
    report = run.get("report")
    if not isinstance(report, dict):
        raise HTTPException(
            status_code=502,
            detail="Agent returned no report dict — parse or model error",
        )

    gate = evaluate_gate(report)
    validation = _validator.validate(dict(report))

    rid = f"rpt_{uuid.uuid4().hex[:12]}"
    entry = ReportEntry(
        report_id=rid,
        brief=body.brief,
        report=report,
        gate=gate,
        input_tokens=run.get("input_tokens"),
        output_tokens=run.get("output_tokens"),
        tokens_used=run.get("tokens_used"),
    )
    state.reports.append(entry)
    store.save_session(state)

    return {
        "session_id": body.session_id,
        "report_id": rid,
        "report": report,
        "gate": gate.model_dump(mode="json"),
        "validation": validation,
        "tokens_used": run.get("tokens_used"),
        "input_tokens": run.get("input_tokens"),
        "output_tokens": run.get("output_tokens"),
        "cache_hit": run.get("cache_hit", False),
    }


@router.get("/{report_id}")
def get_report(report_id: str) -> dict:
    found = store.find_report_session(report_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Report not found")
    session_id, index = found
    state = store.load_session(session_id)
    assert state is not None
    entry = state.reports[index]
    return {
        "session_id": session_id,
        "report_id": entry.report_id,
        "brief": entry.brief,
        "report": entry.report,
        "gate": entry.gate.model_dump(mode="json"),
        "refinements": [r.model_dump(mode="json") for r in entry.refinements],
    }
