"""Read gate state and submit approve / reject decisions."""

from fastapi import APIRouter, Depends, HTTPException
from backend.api.db import store
from backend.api.deps import planr_user_id
from backend.api.models.gate import GateDecisionRequest, GateState
from backend.api.services.feedback_logger import log_gate_decision

router = APIRouter()


@router.get("/{report_id}")
def get_gate(
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
    g = entry.gate
    return {
        "session_id": session_id,
        "report_id": report_id,
        "report_revision": entry.report_revision,
        "gate": g.model_dump(mode="json"),
    }


@router.post("/{report_id}/decision")
def post_decision(
    report_id: str,
    body: GateDecisionRequest,
    user_id: str = Depends(planr_user_id),
) -> dict:
    found = store.find_report_session(user_id, report_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Report not found")
    session_id, index = found
    if session_id != body.session_id:
        raise HTTPException(
            status_code=400,
            detail="session_id does not match report location",
        )

    state = store.load_session(user_id, session_id)
    assert state is not None
    entry = state.reports[index]

    if body.expected_revision is not None and body.expected_revision != entry.report_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "report_revision_conflict",
                "current_revision": entry.report_revision,
                "expected_revision": body.expected_revision,
            },
        )

    entry.gate = GateState(
        fired=entry.gate.fired,
        reasons=entry.gate.reasons,
        decision=body.decision,
    )
    entry.report_revision += 1
    store.save_session(user_id, state)

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
        "report_revision": entry.report_revision,
        "gate": entry.gate.model_dump(mode="json"),
    }
