"""GET /reports/{id} and GET /gates/{id} — happy path + 404."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.models.gate import GateState
from backend.api.models.session import ReportEntry, SessionState

client = TestClient(app)

HEADERS = {"X-Planr-User": "test-read-user"}
REPORT_ID = "rpt_read_test_001"
SESSION_ID = "ses_read_test_001"

_GATE = GateState(fired=False, reasons=[], decision=None)
_REPORT = {"pm_confidence_score": {"score": 75}}


def _state() -> SessionState:
    entry = ReportEntry(
        report_id=REPORT_ID,
        brief="Build a dashboard",
        report=_REPORT,
        gate=_GATE,
        report_revision=1,
    )
    return SessionState(session_id=SESSION_ID, reports=[entry])


# ---------------------------------------------------------------------------
# GET /reports/{report_id}
# ---------------------------------------------------------------------------

def test_get_report_happy_path():
    state = _state()
    with (
        patch(
            "backend.api.routers.reports.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.reports.store.load_session", return_value=state),
    ):
        resp = client.get(f"/reports/{REPORT_ID}", headers=HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["report_id"] == REPORT_ID
    assert "report" in body
    assert "gate" in body
    assert "refinements" in body
    assert "report_revision" in body


def test_get_report_not_found():
    with patch(
        "backend.api.routers.reports.store.find_report_session",
        return_value=None,
    ):
        resp = client.get("/reports/rpt_does_not_exist", headers=HEADERS)

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /gates/{report_id}
# ---------------------------------------------------------------------------

def test_get_gate_happy_path():
    state = _state()
    with (
        patch(
            "backend.api.routers.gates.store.find_report_session",
            return_value=(SESSION_ID, 0),
        ),
        patch("backend.api.routers.gates.store.load_session", return_value=state),
    ):
        resp = client.get(f"/gates/{REPORT_ID}", headers=HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert "gate" in body
    assert "report_revision" in body
    assert body["report_id"] == REPORT_ID


def test_get_gate_not_found():
    with patch(
        "backend.api.routers.gates.store.find_report_session",
        return_value=None,
    ):
        resp = client.get("/gates/rpt_does_not_exist", headers=HEADERS)

    assert resp.status_code == 404
