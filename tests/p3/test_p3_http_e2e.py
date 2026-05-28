"""
HTTP-level E2E tests for POST /reports/generate with P3 pipeline.

Tests the full request-to-response path:
  classify_input → get_orchestrator().run() → sync_pm_confidence → validate
  → evaluate_gate → ReportEntry → save_session → JSON response

Orchestrator is mocked at the get_orchestrator() boundary — no real API calls.
Uses TC-04 fixture data (simplest brief, 80.0 confidence score) as the
representative happy-path response.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.models.gate import GateState
from backend.api.models.session import SessionState
from schemas.partial_schemas import PipelineResult, TokenTally

client = TestClient(app)
HEADERS = {"X-Planr-User": "e2e-test-user"}

_FIXTURE_DIR = Path(__file__).parent.parent.parent / "inputs" / "test-cases-p3" / "fixtures"

_PM_REPORT_REQUIRED_KEYS = [
    "project_understanding", "assumption_log", "open_questions",
    "report_metadata", "use_case_model", "project_plan",
    "use_case_task_mapping", "risk_register", "risk_use_case_mapping",
    "critical_path_risk_flags", "staffing_plan", "actor_role_mapping",
    "project_viability", "pm_confidence_score",
]

_BRIEF = (
    Path(__file__).parent.parent.parent
    / "inputs" / "test-cases-p3" / "tc-04-simple.txt"
).read_text(encoding="utf-8")


def _load(agent: str, tc: str = "tc-04-simple") -> dict:
    return json.loads((_FIXTURE_DIR / agent / f"{tc}.json").read_text(encoding="utf-8"))


def _make_pipeline_result(tc: str = "tc-04-simple", score: float = 80.0) -> PipelineResult:
    """Build a PipelineResult from fixture data, identical to what the orchestrator produces."""
    uc       = _load("use_case",  tc)
    intake   = _load("intake",    tc)
    plan     = _load("planning",  tc)
    risk     = _load("risk",      tc)
    staffing = _load("staffing",  tc)
    synth    = _load("synthesis", tc)

    synth_score = dict(synth.get("pm_confidence_score", {}))
    synth_score["score"] = score
    synth_patched = {**synth, "pm_confidence_score": synth_score}

    report = {
        "project_understanding":    intake.get("project_understanding", {}),
        "assumption_log":           intake.get("assumption_log", []),
        "open_questions":           (staffing.get("open_questions") or [])
                                    + (synth.get("added_open_questions") or []),
        "report_metadata":          intake.get("report_metadata", {}),
        "use_case_model":           uc,
        "project_plan":             plan.get("project_plan", {}),
        "use_case_task_mapping":    plan.get("use_case_task_mapping", {}),
        "risk_register":            risk.get("risk_register", []),
        "risk_use_case_mapping":    risk.get("risk_use_case_mapping", {}),
        "critical_path_risk_flags": risk.get("critical_path_risk_flags", []),
        "staffing_plan":            staffing.get("staffing_plan", []),
        "actor_role_mapping":       staffing.get("actor_role_mapping", {}),
        "project_viability":        staffing.get("project_viability", {}),
        "pm_confidence_score":      synth_patched["pm_confidence_score"],
    }

    tally = TokenTally(input_tokens=3000, output_tokens=1800)
    return PipelineResult(
        final_report=report,
        synthesis_corrections=synth.get("corrections_applied", []),
        partial_artifacts={},
        token_tally=tally,
    )


def _post(brief: str = _BRIEF, session_id: str = "ses-e2e-01",
          pipeline_result=None, gate_override=None):
    pr = pipeline_result or _make_pipeline_result()
    mock_orch = MagicMock()
    mock_orch.run = AsyncMock(return_value=pr)

    with (
        patch("backend.api.routers.reports.get_orchestrator", return_value=mock_orch),
        patch("backend.api.routers.reports.evaluate_gate",
              return_value=gate_override or GateState(fired=False, reasons=[])),
        patch("backend.api.routers.reports.store") as mock_store,
        patch("backend.api.routers.reports.sync_pm_confidence_metadata_mirrors"),
        patch("backend.api.routers.reports._validator") as mock_validator,
    ):
        mock_store.load_session.return_value = None
        mock_store.save_session.return_value = None
        mock_validator.validate.return_value = {"valid": True, "errors": []}
        resp = client.post(
            "/reports/generate",
            json={"brief": brief, "session_id": session_id},
            headers=HEADERS,
        )
        return resp, mock_orch, mock_store


# ---------------------------------------------------------------------------
# Happy-path response shape
# ---------------------------------------------------------------------------

def test_generate_returns_200():
    resp, _, _ = _post()
    assert resp.status_code == 200, resp.json()


def test_generate_response_has_all_top_level_keys():
    resp, _, _ = _post()
    body = resp.json()
    for key in ("session_id", "report_id", "report_revision", "report", "gate",
                "validation", "tokens_used", "input_tokens", "output_tokens"):
        assert key in body, f"Missing top-level key: {key}"


def test_generate_report_has_all_pm_report_keys():
    resp, _, _ = _post()
    report = resp.json()["report"]
    missing = [k for k in _PM_REPORT_REQUIRED_KEYS if k not in report]
    assert not missing, f"PMReport missing keys: {missing}"


def test_generate_pm_confidence_score_correct():
    resp, _, _ = _post()
    score = resp.json()["report"]["pm_confidence_score"]["score"]
    assert score == 80.0


def test_generate_token_tally_in_response():
    resp, _, _ = _post()
    body = resp.json()
    assert body["input_tokens"] == 3000
    assert body["output_tokens"] == 1800
    assert body["tokens_used"] == 4800


def test_generate_report_id_format():
    resp, _, _ = _post()
    rid = resp.json()["report_id"]
    assert rid.startswith("rpt_")
    assert len(rid) > 4


def test_generate_session_saved():
    resp, _, mock_store = _post(session_id="ses-save-test")
    assert resp.status_code == 200
    mock_store.save_session.assert_called_once()
    saved_state = mock_store.save_session.call_args[0][1]
    assert len(saved_state.reports) == 1
    assert saved_state.reports[0].report_id.startswith("rpt_")


def test_generate_orchestrator_called_with_correct_args():
    resp, mock_orch, _ = _post(session_id="ses-args-check")
    mock_orch.run.assert_called_once()
    call_kwargs = mock_orch.run.call_args.kwargs
    assert call_kwargs["session_id"] == "ses-args-check"
    assert call_kwargs["user_id"] == "e2e-test-user"
    assert "tc-04" in call_kwargs["raw_brief"] or len(call_kwargs["raw_brief"]) > 100


# ---------------------------------------------------------------------------
# Gate behavior
# ---------------------------------------------------------------------------

def test_generate_evaluate_gate_runs_on_final_report():
    """evaluate_gate must be called once with the assembled report."""
    pr = _make_pipeline_result()
    mock_orch = MagicMock()
    mock_orch.run = AsyncMock(return_value=pr)
    gate_mock = MagicMock(return_value=GateState(fired=True, reasons=["High risk"]))

    with (
        patch("backend.api.routers.reports.get_orchestrator", return_value=mock_orch),
        patch("backend.api.routers.reports.evaluate_gate", gate_mock),
        patch("backend.api.routers.reports.store") as mock_store,
        patch("backend.api.routers.reports.sync_pm_confidence_metadata_mirrors"),
        patch("backend.api.routers.reports._validator") as mock_validator,
    ):
        mock_store.load_session.return_value = None
        mock_store.save_session.return_value = None
        mock_validator.validate.return_value = {"valid": True}
        resp = client.post(
            "/reports/generate",
            json={"brief": _BRIEF, "session_id": "ses-gate-check"},
            headers=HEADERS,
        )

    assert resp.status_code == 200
    gate_mock.assert_called_once()
    assert resp.json()["gate"]["fired"] is True


def test_generate_intake_gate_returns_422():
    """When the orchestrator returns paused_at='intake', the endpoint returns 422."""
    failed_result = PipelineResult(
        paused_at="intake",
        gate_signal="Gate triggered: input quality is LOW",
        partial_artifacts={},
        token_tally=TokenTally(),
    )
    mock_orch = MagicMock()
    mock_orch.run = AsyncMock(return_value=failed_result)

    with (
        patch("backend.api.routers.reports.get_orchestrator", return_value=mock_orch),
        patch("backend.api.routers.reports.store") as mock_store,
        patch("backend.api.routers.reports.sync_pm_confidence_metadata_mirrors"),
    ):
        mock_store.load_session.return_value = None
        resp = client.post(
            "/reports/generate",
            json={"brief": _BRIEF, "session_id": "ses-intake-gate"},
            headers=HEADERS,
        )

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "intake_gate"
    assert "LOW" in detail["gate_signal"]
    mock_store.save_session.assert_not_called()


def test_generate_intake_gate_does_not_save_session():
    """On gate fire, nothing should be persisted."""
    failed_result = PipelineResult(
        paused_at="intake",
        gate_signal="Gate triggered: 7 assumptions exceed the 5-assumption threshold",
        partial_artifacts={},
        token_tally=TokenTally(),
    )
    mock_orch = MagicMock()
    mock_orch.run = AsyncMock(return_value=failed_result)

    with (
        patch("backend.api.routers.reports.get_orchestrator", return_value=mock_orch),
        patch("backend.api.routers.reports.store") as mock_store,
        patch("backend.api.routers.reports.sync_pm_confidence_metadata_mirrors"),
    ):
        mock_store.load_session.return_value = None
        client.post(
            "/reports/generate",
            json={"brief": _BRIEF, "session_id": "ses-no-save"},
            headers=HEADERS,
        )

    mock_store.save_session.assert_not_called()


# ---------------------------------------------------------------------------
# All four TCs produce correct pm_confidence score via HTTP
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tc,expected_score", [
    ("tc-01-perfect", 40.0),
    ("tc-02-good",    40.0),
    ("tc-03-medium",  20.0),
    ("tc-04-simple",  80.0),
])
def test_all_tcs_correct_score_through_http(tc, expected_score):
    pr = _make_pipeline_result(tc=tc, score=expected_score)
    resp, _, _ = _post(session_id=f"ses-{tc}", pipeline_result=pr)
    assert resp.status_code == 200, resp.json()
    assert resp.json()["report"]["pm_confidence_score"]["score"] == expected_score
