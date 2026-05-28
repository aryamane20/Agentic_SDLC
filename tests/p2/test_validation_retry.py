"""
Tests for POST /reports/generate validation behavior in P3.

P2 had a 3-attempt retry loop. P3 removed it — the orchestrator handles
per-agent retries internally. The validator is now called once; a non-valid
result is advisory and does not block the 200 response.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.models.gate import GateState
from backend.api.models.session import SessionState

client = TestClient(app)
HEADERS = {"X-Planr-User": "test-retry-user"}
SESSION_ID = "ses-retry-test"

_MOCK_GATE = GateState(fired=False, reasons=[], decision=None)

_MOCK_REPORT = {
    "pm_confidence_score": {"score": 75},
    "assumption_log": [],
    "project_plan": {},
    "risk_register": [],
    "staffing_plan": [],
    "open_questions": [],
    "report_metadata": {},
    "project_understanding": {},
    "use_case_model": {},
    "use_case_task_mapping": {},
    "risk_use_case_mapping": {},
    "critical_path_risk_flags": [],
    "actor_role_mapping": {},
    "project_viability": {},
}

_GENERATE_BODY = {
    "session_id": SESSION_ID,
    "brief": "Build a reporting dashboard for finance",
    "use_cache": True,
}


def _make_orchestrator(report=None):
    tally = MagicMock()
    tally.input_tokens = 10
    tally.output_tokens = 20
    tally.total_tokens = 30

    pipeline_result = MagicMock()
    pipeline_result.succeeded = True
    pipeline_result.final_report = dict(report or _MOCK_REPORT)
    pipeline_result.token_tally = tally

    orch = MagicMock()
    orch.run = AsyncMock(return_value=pipeline_result)
    return orch


def test_pipeline_result_validated_once():
    """P3: pipeline runs once, validator called once, 200 returned."""
    orch = _make_orchestrator()
    validate_mock = MagicMock(return_value={"valid": True, "errors": []})
    state = SessionState(session_id=SESSION_ID)

    with (
        patch("backend.api.routers.reports.get_orchestrator", return_value=orch),
        patch("backend.api.routers.reports._validator.validate", validate_mock),
        patch("backend.api.routers.reports.store.load_session", return_value=state),
        patch("backend.api.routers.reports.store.save_session"),
        patch("backend.api.routers.reports.evaluate_gate", return_value=_MOCK_GATE),
        patch("backend.api.routers.reports.sync_pm_confidence_metadata_mirrors"),
    ):
        resp = client.post("/reports/generate", headers=HEADERS, json=_GENERATE_BODY)

    assert resp.status_code == 200
    orch.run.assert_called_once()
    validate_mock.assert_called_once()


def test_validation_failure_still_returns_200():
    """P3: schema validation is advisory — invalid result still returns 200."""
    orch = _make_orchestrator()
    validate_mock = MagicMock(return_value={"valid": False, "errors": ["missing field"]})
    state = SessionState(session_id=SESSION_ID)

    with (
        patch("backend.api.routers.reports.get_orchestrator", return_value=orch),
        patch("backend.api.routers.reports._validator.validate", validate_mock),
        patch("backend.api.routers.reports.store.load_session", return_value=state),
        patch("backend.api.routers.reports.store.save_session"),
        patch("backend.api.routers.reports.evaluate_gate", return_value=_MOCK_GATE),
        patch("backend.api.routers.reports.sync_pm_confidence_metadata_mirrors"),
    ):
        resp = client.post("/reports/generate", headers=HEADERS, json=_GENERATE_BODY)

    assert resp.status_code == 200
    body = resp.json()
    assert body["validation"]["valid"] is False
    orch.run.assert_called_once()
