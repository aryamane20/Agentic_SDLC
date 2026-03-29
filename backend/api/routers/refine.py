"""POST /reports/{report_id}/refine — MVP full re-run with feedback (partial steps later)."""

from functools import lru_cache

from fastapi import APIRouter, HTTPException

from agent.main import PMAgent

from backend.api.db import store
from backend.api.models.gate import RefineRequest
from backend.api.models.session import RefinementRecord
from backend.api.services.approval_gate import evaluate_gate
from backend.api.services.refinement import run_refinement

router = APIRouter()


@lru_cache(maxsize=8)
def _agent_for_version(prompt_version: str) -> PMAgent:
    return PMAgent(prompt_version=prompt_version)


@router.post("/reports/{report_id}/refine")
def refine(report_id: str, body: RefineRequest) -> dict:
    found = store.find_report_session(report_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Report not found")
    session_id, index = found
    if session_id != body.session_id:
        raise HTTPException(
            status_code=400,
            detail="session_id does not match report location",
        )

    state = store.load_session(session_id)
    assert state is not None
    entry = state.reports[index]

    prior = entry.report
    if entry.refinements:
        prior = entry.refinements[-1].report

    agent = _agent_for_version("v1.6.1")
    out = run_refinement(
        agent=agent,
        original_brief=entry.brief,
        previous_report=prior,
        feedback=body.feedback,
    )
    new_report = out["report"]
    gate = evaluate_gate(new_report)

    entry.refinements.append(
        RefinementRecord(
            feedback=body.feedback,
            report=new_report,
            gate=gate,
        )
    )
    entry.report = new_report
    entry.gate = gate
    store.save_session(state)

    return {
        "session_id": session_id,
        "report_id": report_id,
        "report": new_report,
        "gate": gate.model_dump(mode="json"),
        "refinement_count": len(entry.refinements),
        "tokens_used": out.get("tokens_used"),
        "input_tokens": out.get("input_tokens"),
        "output_tokens": out.get("output_tokens"),
    }
