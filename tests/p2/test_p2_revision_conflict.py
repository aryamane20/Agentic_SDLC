"""Optimistic concurrency: 409 when expected_revision does not match report_revision."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.models.gate import GateState
from backend.api.models.session import ReportEntry, SessionState

client = TestClient(app)

HEADERS = {"X-Planr-User": "test-user-rev"}
REPORT_ID = "rpt_rev_conflict"
SESSION_ID = "ses_rev_conflict"

_GATE = GateState(
    fired=True,
    reasons=["confidence_score < 60 — plan needs review"],
    decision=None,
)

_MOCK_REFINE = {
    "report": {"pm_confidence_score": {"score": 72}},
    "gate": GateState(fired=False, reasons=[], decision=None).model_dump(mode="json"),
    "tokens_used": 1,
    "input_tokens": 1,
    "output_tokens": 1,
}


def _entry(revision: int = 1) -> ReportEntry:
    return ReportEntry(
        report_id=REPORT_ID,
        brief="Brief",
        report={"pm_confidence_score": {"score": 55}},
        gate=_GATE,
        report_revision=revision,
    )


def _state(revision: int = 1) -> SessionState:
    return SessionState(session_id=SESSION_ID, reports=[_entry(revision)])


def test_refine_returns_422_when_expected_revision_negative():
    """expected_revision=-1 violates ge=1 constraint — Pydantic must reject with 422."""
    resp = client.post(
        f"/reports/{REPORT_ID}/refine",
        headers=HEADERS,
        json={
            "session_id": SESSION_ID,
            "feedback": "Some feedback",
            "expected_revision": -1,
        },
    )
    assert resp.status_code == 422


def test_refine_returns_409_when_expected_revision_stale():
    """Another client already refined — current revision is 2, caller still has 1."""
    state = _state(revision=2)
    with (
        patch("backend.api.routers.refine._agent_for_version", return_value=object()),
        patch(
            "backend.api.routers.refine.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.refine.store.load_session", return_value=state),
        patch("backend.api.routers.refine.store.save_session") as mock_save,
        patch("backend.api.routers.refine.run_refinement") as mock_run,
    ):
        resp = client.post(
            f"/reports/{REPORT_ID}/refine",
            headers=HEADERS,
            json={
                "session_id": SESSION_ID,
                "feedback": "Stale tab",
                "expected_revision": 1,
            },
        )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["error"] == "report_revision_conflict"
    assert detail["current_revision"] == 2
    assert detail["expected_revision"] == 1
    mock_run.assert_not_called()
    mock_save.assert_not_called()


def test_refine_succeeds_when_expected_revision_matches():
    state = _state(revision=1)
    with (
        patch("backend.api.routers.refine._agent_for_version", return_value=object()),
        patch(
            "backend.api.routers.refine.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.refine.store.load_session", return_value=state),
        patch("backend.api.routers.refine.store.save_session"),
        patch("backend.api.routers.refine.run_refinement", return_value=_MOCK_REFINE),
    ):
        resp = client.post(
            f"/reports/{REPORT_ID}/refine",
            headers=HEADERS,
            json={
                "session_id": SESSION_ID,
                "feedback": "OK",
                "expected_revision": 1,
            },
        )
    assert resp.status_code == 200
    assert resp.json()["report_revision"] == 2
    assert state.reports[0].report_revision == 2


def test_gate_decision_returns_409_when_expected_revision_stale():
    state = _state(revision=3)
    with (
        patch(
            "backend.api.routers.gates.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.gates.store.load_session", return_value=state),
        patch("backend.api.routers.gates.log_gate_decision"),
    ):
        resp = client.post(
            f"/gates/{REPORT_ID}/decision",
            headers=HEADERS,
            json={
                "session_id": SESSION_ID,
                "decision": "approve",
                "expected_revision": 1,
            },
        )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["current_revision"] == 3


def test_gate_decision_succeeds_when_expected_revision_matches():
    state = _state(revision=1)
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
            json={
                "session_id": SESSION_ID,
                "decision": "approve",
                "expected_revision": 1,
            },
        )
    assert resp.status_code == 200
    assert resp.json()["report_revision"] == 2
    assert state.reports[0].report_revision == 2
