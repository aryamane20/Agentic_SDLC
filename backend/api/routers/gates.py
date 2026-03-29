"""Read gate state and submit approve / reject decisions."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.db import store
from backend.api.models.gate import GateState
from backend.api.services.feedback_logger import log_gate_decision

router = APIRouter()


class _GateDecisionBody(BaseModel):
    session_id: str = Field(..., min_length=1)
    decision: Literal["approve", "reject"]


@router.get("/{report_id}")
def get_gate(report_id: str) -> dict:
    found = store.find_report_session(report_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Report not found")
    session_id, index = found
    state = store.load_session(session_id)
    assert state is not None
    g = state.reports[index].gate
    return {
        "session_id": session_id,
        "report_id": report_id,
        "gate": g.model_dump(mode="json"),
    }


@router.post("/{report_id}/decision")
def post_decision(report_id: str, body: _GateDecisionBody) -> dict:
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

    entry.gate = GateState(
        fired=entry.gate.fired,
        reasons=entry.gate.reasons,
        decision=body.decision,
    )
    store.save_session(state)

    log_gate_decision(
        session_id=session_id,
        report_id=report_id,
        decision=body.decision,
        gate_fired=entry.gate.fired,
        reasons=list(entry.gate.reasons),
    )

    return {
        "session_id": session_id,
        "report_id": report_id,
        "gate": entry.gate.model_dump(mode="json"),
    }
