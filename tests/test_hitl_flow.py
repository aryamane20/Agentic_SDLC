"""
Integration tests: HITL gate-as-warning model + refinement flow.

Design: The gate is an informational signal, NOT a workflow lock.
  - generate → gate fires → PM can still refine (feedback IS their response)
  - generate → gate fires → PM can approve (formal close)
  - generate → gate fires → PM can start over (separate frontend action, not tested here)
  - Gate is re-evaluated on every new report after refine

All I/O (store, agent, run_refinement) is mocked — no API keys or disk needed.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.models.gate import GateState
from backend.api.models.session import ReportEntry, SessionState

client = TestClient(app)

HEADERS = {"X-Planr-User": "test-user"}

REPORT_ID = "rpt_aabbccddeeff"
SESSION_ID = "ses_test123"

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_state(gate: GateState) -> SessionState:
    entry = ReportEntry(
        report_id=REPORT_ID,
        brief="Build an internal analytics dashboard",
        report={"pm_confidence_score": {"score": 55}},
        gate=gate,
    )
    return SessionState(session_id=SESSION_ID, reports=[entry])


_FIRED_NO_DECISION = GateState(
    fired=True,
    reasons=["confidence_score < 60 — plan needs review"],
    decision=None,
)
_FIRED_APPROVED = GateState(
    fired=True,
    reasons=["confidence_score < 60 — plan needs review"],
    decision="approve",
)
_NOT_FIRED = GateState(fired=False, reasons=[], decision=None)

_MOCK_REFINE_RESULT = {
    "report": {"pm_confidence_score": {"score": 72}},
    "gate": GateState(fired=False, reasons=[], decision=None).model_dump(mode="json"),
    "tokens_used": 300,
    "input_tokens": 200,
    "output_tokens": 100,
}

# Shared mock agent — avoids real PMAgent.__init__ (hits Anthropic client / network)
_MOCK_AGENT = object()


# ── core flow: gate is a warning, not a lock ─────────────────────────────────


def test_refine_allowed_when_gate_fired_and_undecided():
    """
    Gate fires but PM can still refine — feedback is their response to the concerns.
    The gate gets re-evaluated on the resulting report.
    """
    state = _make_state(_FIRED_NO_DECISION)
    with (
        patch("backend.api.routers.refine._agent_for_version", return_value=_MOCK_AGENT),
        patch(
            "backend.api.routers.refine.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.refine.store.load_session", return_value=state),
        patch("backend.api.routers.refine.store.save_session"),
        patch(
            "backend.api.routers.refine.run_refinement",
            return_value=_MOCK_REFINE_RESULT,
        ),
    ):
        resp = client.post(
            f"/reports/{REPORT_ID}/refine",
            headers=HEADERS,
            json={"session_id": SESSION_ID, "feedback": "Increase QA budget to address risk"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_id"] == REPORT_ID
    assert body["refinement_count"] == 1
    # Gate on new report is re-evaluated — cleared in mock result
    assert body["gate"]["fired"] is False


def test_refine_allowed_after_gate_approved():
    """200 when gate fired and PM has already approved — PM continues to refine further."""
    state = _make_state(_FIRED_APPROVED)
    with (
        patch("backend.api.routers.refine._agent_for_version", return_value=_MOCK_AGENT),
        patch(
            "backend.api.routers.refine.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.refine.store.load_session", return_value=state),
        patch("backend.api.routers.refine.store.save_session"),
        patch(
            "backend.api.routers.refine.run_refinement",
            return_value=_MOCK_REFINE_RESULT,
        ),
    ):
        resp = client.post(
            f"/reports/{REPORT_ID}/refine",
            headers=HEADERS,
            json={"session_id": SESSION_ID, "feedback": "Increase QA budget"},
        )
    assert resp.status_code == 200
    assert resp.json()["refinement_count"] == 1


def test_refine_allowed_when_gate_never_fired():
    """200 immediately when gate did not fire — clean plan, no human action needed."""
    state = _make_state(_NOT_FIRED)
    with (
        patch("backend.api.routers.refine._agent_for_version", return_value=_MOCK_AGENT),
        patch(
            "backend.api.routers.refine.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.refine.store.load_session", return_value=state),
        patch("backend.api.routers.refine.store.save_session"),
        patch(
            "backend.api.routers.refine.run_refinement",
            return_value=_MOCK_REFINE_RESULT,
        ),
    ):
        resp = client.post(
            f"/reports/{REPORT_ID}/refine",
            headers=HEADERS,
            json={"session_id": SESSION_ID, "feedback": "Tighten the risk register"},
        )
    assert resp.status_code == 200


# ── gate is not double-evaluated ──────────────────────────────────────────────


def test_refine_does_not_call_evaluate_gate_twice():
    """
    run_refinement already evaluates the gate internally.
    The router must NOT import or call evaluate_gate a second time.
    Verified by asserting evaluate_gate is not an attribute of the refine module.
    """
    import backend.api.routers.refine as refine_module
    assert not hasattr(refine_module, "evaluate_gate"), (
        "refine.py imported evaluate_gate directly — gate is being evaluated twice. "
        "Use GateState.model_validate(out['gate']) instead."
    )

    state = _make_state(_NOT_FIRED)
    with (
        patch("backend.api.routers.refine._agent_for_version", return_value=_MOCK_AGENT),
        patch(
            "backend.api.routers.refine.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.refine.store.load_session", return_value=state),
        patch("backend.api.routers.refine.store.save_session"),
        patch(
            "backend.api.routers.refine.run_refinement",
            return_value=_MOCK_REFINE_RESULT,
        ) as mock_run,
    ):
        resp = client.post(
            f"/reports/{REPORT_ID}/refine",
            headers=HEADERS,
            json={"session_id": SESSION_ID, "feedback": "Tighten the risk register"},
        )
    assert resp.status_code == 200
    mock_run.assert_called_once()


# ── approve records decision and gate state ───────────────────────────────────


def test_approve_records_decision_on_fired_gate():
    """Approve stores decision=approve and returns the updated gate state."""
    state = _make_state(_FIRED_NO_DECISION)
    with (
        patch(
            "backend.api.routers.gates.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.gates.store.load_session", return_value=state),
        patch("backend.api.routers.gates.store.save_session"),
        patch("backend.api.routers.gates.log_gate_decision"),
    ):
        resp = client.post(
            f"/gates/{REPORT_ID}/decision",
            headers=HEADERS,
            json={"session_id": SESSION_ID, "decision": "approve"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["gate"]["decision"] == "approve"
    assert body["gate"]["fired"] is True  # fired status unchanged — decision is the overlay


def test_approve_records_decision_on_clean_gate():
    """Approve also works when gate never fired — PM signs off on a clean plan."""
    state = _make_state(_NOT_FIRED)
    with (
        patch(
            "backend.api.routers.gates.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.gates.store.load_session", return_value=state),
        patch("backend.api.routers.gates.store.save_session"),
        patch("backend.api.routers.gates.log_gate_decision"),
    ):
        resp = client.post(
            f"/gates/{REPORT_ID}/decision",
            headers=HEADERS,
            json={"session_id": SESSION_ID, "decision": "approve"},
        )
    assert resp.status_code == 200
    assert resp.json()["gate"]["decision"] == "approve"


# ── error cases ───────────────────────────────────────────────────────────────


def test_refine_session_id_mismatch_returns_400():
    """Wrong session_id in body → 400 regardless of gate state."""
    state = _make_state(_NOT_FIRED)
    with (
        patch("backend.api.routers.refine._agent_for_version", return_value=_MOCK_AGENT),
        patch(
            "backend.api.routers.refine.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.refine.store.load_session", return_value=state),
    ):
        resp = client.post(
            f"/reports/{REPORT_ID}/refine",
            headers=HEADERS,
            json={"session_id": "ses_WRONG", "feedback": "Some feedback"},
        )
    assert resp.status_code == 400


def test_refine_report_not_found_returns_404():
    with patch(
        "backend.api.routers.refine.store.find_report_session",
        return_value=None,
    ):
        resp = client.post(
            "/reports/rpt_doesnotexist/refine",
            headers=HEADERS,
            json={"session_id": SESSION_ID, "feedback": "Some feedback"},
        )
    assert resp.status_code == 404
