"""Validation retry loop in POST /reports/generate.

_MAX_VALIDATION_ATTEMPTS = 3:
- On invalid output the agent is re-run (cache busted).
- After exhausting all attempts the last report is returned (no crash, no 500).
"""

from unittest.mock import MagicMock, call, patch

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.models.session import SessionState

client = TestClient(app)

HEADERS = {"X-Planr-User": "test-retry-user"}
SESSION_ID = "ses-retry-test"

_VALID_REPORT = {
    "pm_confidence_score": {"score": 75},
    "risk_register": [],
    "open_questions": [],
}

_VALID_RUN = {
    "report": _VALID_REPORT,
    "input_tokens": 10,
    "output_tokens": 20,
    "tokens_used": 30,
    "cache_hit": False,
}

_GENERATE_BODY = {
    "session_id": SESSION_ID,
    "brief": "Build a reporting dashboard for finance",
    "use_cache": True,
}


def _mock_agent():
    agent = MagicMock()
    agent.run.return_value = dict(_VALID_RUN)
    agent._enforce_hard_caps.return_value = None
    return agent


def test_retry_succeeds_on_third_attempt():
    """Agent returns invalid output twice; third attempt is valid → 200, run called 3 times."""
    agent = _mock_agent()
    # Validator: invalid, invalid, valid
    validate_results = [
        {"valid": False, "errors": ["missing field"]},
        {"valid": False, "errors": ["missing field"]},
        {"valid": True, "errors": []},
    ]
    validate_mock = MagicMock(side_effect=validate_results)
    state = SessionState(session_id=SESSION_ID)

    with (
        patch("backend.api.routers.reports._agent_for_version", return_value=agent),
        patch("backend.api.routers.reports._validator.validate", validate_mock),
        patch("backend.api.routers.reports.store.load_session", return_value=state),
        patch("backend.api.routers.reports.store.save_session"),
        patch("backend.api.routers.reports.time.sleep"),
        patch("backend.api.routers.reports.sync_pm_confidence_metadata_mirrors"),
    ):
        resp = client.post("/reports/generate", headers=HEADERS, json=_GENERATE_BODY)

    assert resp.status_code == 200
    assert agent.run.call_count == 3
    # First call uses cache, subsequent calls bust it
    calls = agent.run.call_args_list
    assert calls[0].kwargs.get("use_cache", True) is True
    assert calls[1].kwargs.get("use_cache", True) is False
    assert calls[2].kwargs.get("use_cache", True) is False


def test_retry_exhausted_returns_200_not_500():
    """All 3 attempts return invalid output — no crash, no 500, loop terminates cleanly."""
    agent = _mock_agent()
    validate_mock = MagicMock(return_value={"valid": False, "errors": ["bad schema"]})
    state = SessionState(session_id=SESSION_ID)

    with (
        patch("backend.api.routers.reports._agent_for_version", return_value=agent),
        patch("backend.api.routers.reports._validator.validate", validate_mock),
        patch("backend.api.routers.reports.store.load_session", return_value=state),
        patch("backend.api.routers.reports.store.save_session"),
        patch("backend.api.routers.reports.time.sleep"),
        patch("backend.api.routers.reports.sync_pm_confidence_metadata_mirrors"),
    ):
        resp = client.post("/reports/generate", headers=HEADERS, json=_GENERATE_BODY)

    assert resp.status_code == 200
    assert agent.run.call_count == 3
