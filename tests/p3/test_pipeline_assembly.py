"""
Fixture-based pipeline assembly tests.

Each test feeds the pre-computed fixture outputs (from real Haiku API runs)
through the orchestrator and verifies that the assembled PMReport is correct.

This catches regressions in:
  - _assemble_report() merging logic
  - pm_confidence.py overriding the LLM's arithmetic
  - synthesis corrections being applied to the staffing plan
  - open questions merged from staffing + synthesis
  - gate routing (none of the TCs should trigger the intake gate)
  - report passing schema validation

No Anthropic API calls — all 6 agents are mocked with fixture data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, patch

from agent.orchestrator import PipelineOrchestrator
from agent.validator import SchemaValidator

_FIXTURE_DIR = Path(__file__).parent.parent.parent / "inputs" / "test-cases-p3" / "fixtures"
_BRIEF_DIR   = Path(__file__).parent.parent.parent / "inputs" / "test-cases-p3"

_VALIDATOR = SchemaValidator()

_PM_REPORT_REQUIRED_KEYS = {
    "project_understanding",
    "assumption_log",
    "open_questions",
    "report_metadata",
    "use_case_model",
    "project_plan",
    "use_case_task_mapping",
    "risk_register",
    "risk_use_case_mapping",
    "critical_path_risk_flags",
    "staffing_plan",
    "actor_role_mapping",
    "project_viability",
    "pm_confidence_score",
}

# Python-computed authoritative scores (LLM values differ — see test_pm_confidence.py)
_EXPECTED_SCORES = {
    "tc-01-perfect": 40.0,
    "tc-02-good":    40.0,
    "tc-03-medium":  20.0,
    "tc-04-simple":  80.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(agent: str, tc: str) -> dict:
    return json.loads((_FIXTURE_DIR / agent / f"{tc}.json").read_text(encoding="utf-8"))


def _brief(tc: str) -> str:
    p = _BRIEF_DIR / f"{tc}.txt"
    return p.read_text(encoding="utf-8") if p.exists() else f"Brief for {tc}"


def _result(artifact: dict) -> dict:
    return {
        "artifact": artifact,
        "input_tokens": 500,
        "output_tokens": 300,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "parse_failed": False,
        "attempts": 1,
        "raw_output": "",
    }


async def _run_pipeline(tc: str) -> dict:
    """Run the orchestrator with fixture data for the given TC. Returns the final report."""
    orchestrator = PipelineOrchestrator.for_testing()
    uc      = _load("use_case", tc)
    intake  = _load("intake",   tc)
    plan    = _load("planning",  tc)
    risk    = _load("risk",      tc)
    staffing = _load("staffing", tc)
    synth   = _load("synthesis", tc)

    with (
        patch("agent.orchestrator.UseCaseAgent")  as MockUC,
        patch("agent.orchestrator.IntakeAgent")   as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent")     as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        MockUC.return_value.run_async    = AsyncMock(return_value=_result(uc))
        MockInt.return_value.run_async   = AsyncMock(return_value=_result(intake))
        MockPlan.return_value.run_async  = AsyncMock(return_value=_result(plan))
        MockRisk.return_value.run_async  = AsyncMock(return_value=_result(risk))
        MockStaff.return_value.run_async = AsyncMock(return_value=_result(staffing))
        MockSynth.return_value.run_async = AsyncMock(return_value=_result(synth))

        result = await orchestrator.run(_brief(tc), f"sess-{tc}", "test-user")

    assert result.succeeded, f"Pipeline gate fired unexpectedly: {result.gate_signal}"
    return result.final_report


# ---------------------------------------------------------------------------
# Parametrized: all four TCs assemble a valid PMReport
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("tc", ["tc-01-perfect", "tc-02-good", "tc-03-medium", "tc-04-simple"])
async def test_pipeline_returns_all_required_pm_report_keys(tc):
    report = await _run_pipeline(tc)
    missing = _PM_REPORT_REQUIRED_KEYS - set(report.keys())
    assert not missing, f"{tc}: missing keys {missing}"


@pytest.mark.asyncio
@pytest.mark.parametrize("tc,expected_score", list(_EXPECTED_SCORES.items()))
async def test_pipeline_pm_confidence_python_overrides_llm(tc, expected_score):
    """Python computation must replace the LLM's score (LLM was wrong on TC-01..03)."""
    report = await _run_pipeline(tc)
    actual = report["pm_confidence_score"]["score"]
    assert actual == expected_score, (
        f"{tc}: expected python score {expected_score}, got {actual} "
        "(LLM value not overridden)"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("tc", ["tc-01-perfect", "tc-02-good", "tc-03-medium", "tc-04-simple"])
async def test_pipeline_open_questions_merged(tc):
    """Final report open_questions = staffing questions + synthesis added questions."""
    report   = await _run_pipeline(tc)
    staffing = _load("staffing", tc)
    synth    = _load("synthesis", tc)
    expected = (
        len(staffing.get("open_questions", []))
        + len(synth.get("added_open_questions", []))
    )
    assert len(report["open_questions"]) == expected, (
        f"{tc}: expected {expected} questions, got {len(report['open_questions'])}"
    )


@pytest.mark.asyncio
async def test_tc01_set_critical_path_correction_applied():
    """TC-01 synthesis has a set_critical_path correction — verify it lands in staffing_plan."""
    report = await _run_pipeline("tc-01-perfect")
    synth = _load("synthesis", "tc-01-perfect")
    corr = next((c for c in synth.get("staffing_corrections", [])
                 if c.get("action") == "set_critical_path"), None)
    assert corr is not None, "fixture should have a set_critical_path correction"
    target_role = corr["role"]
    matched = [r for r in report["staffing_plan"] if r.get("role") == target_role]
    assert matched, f"Role '{target_role}' not found in staffing_plan"
    assert matched[0]["critical_path"] is True, (
        f"Role '{target_role}' should have critical_path=True after correction"
    )


@pytest.mark.asyncio
async def test_tc03_add_role_correction_applied():
    """TC-03 synthesis has add_role corrections — verify extra roles appear."""
    report = await _run_pipeline("tc-03-medium")
    synth = _load("synthesis", "tc-03-medium")
    staffing = _load("staffing", "tc-03-medium")
    added = [c for c in synth.get("staffing_corrections", []) if c.get("action") == "add_role"]
    if not added:
        pytest.skip("tc-03 fixture has no add_role corrections")
    original_count = len(staffing.get("staffing_plan", []))
    assert len(report["staffing_plan"]) == original_count + len(added)


@pytest.mark.asyncio
@pytest.mark.parametrize("tc", ["tc-01-perfect", "tc-02-good", "tc-03-medium", "tc-04-simple"])
async def test_pipeline_risk_register_preserved(tc):
    report = await _run_pipeline(tc)
    risk = _load("risk", tc)
    assert len(report["risk_register"]) == len(risk.get("risk_register", []))


@pytest.mark.asyncio
@pytest.mark.parametrize("tc", ["tc-01-perfect", "tc-02-good", "tc-03-medium", "tc-04-simple"])
async def test_pipeline_use_case_model_preserved(tc):
    report = await _run_pipeline(tc)
    uc = _load("use_case", tc)
    assert report["use_case_model"].get("system_boundary") == uc.get("system_boundary")
    assert len(report["use_case_model"].get("use_cases", [])) == len(uc.get("use_cases", []))


@pytest.mark.asyncio
@pytest.mark.parametrize("tc", ["tc-01-perfect", "tc-02-good", "tc-03-medium", "tc-04-simple"])
async def test_pipeline_assumption_log_from_intake(tc):
    report = await _run_pipeline(tc)
    intake = _load("intake", tc)
    assert len(report["assumption_log"]) == len(intake.get("assumption_log", []))


@pytest.mark.asyncio
@pytest.mark.parametrize("tc", ["tc-01-perfect", "tc-02-good", "tc-03-medium", "tc-04-simple"])
async def test_pipeline_no_gate_fires_for_well_formed_brief(tc):
    """All four TCs have HIGH quality and ≤5 assumptions — gate must not fire."""
    orchestrator = PipelineOrchestrator.for_testing()
    uc      = _load("use_case", tc)
    intake  = _load("intake",   tc)
    plan    = _load("planning",  tc)
    risk    = _load("risk",      tc)
    staffing = _load("staffing", tc)
    synth   = _load("synthesis", tc)

    with (
        patch("agent.orchestrator.UseCaseAgent")  as MockUC,
        patch("agent.orchestrator.IntakeAgent")   as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent")     as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        MockUC.return_value.run_async    = AsyncMock(return_value=_result(uc))
        MockInt.return_value.run_async   = AsyncMock(return_value=_result(intake))
        MockPlan.return_value.run_async  = AsyncMock(return_value=_result(plan))
        MockRisk.return_value.run_async  = AsyncMock(return_value=_result(risk))
        MockStaff.return_value.run_async = AsyncMock(return_value=_result(staffing))
        MockSynth.return_value.run_async = AsyncMock(return_value=_result(synth))

        result = await orchestrator.run(_brief(tc), f"sess-gate-{tc}", "test-user")

    assert result.succeeded
    assert result.paused_at is None


@pytest.mark.asyncio
@pytest.mark.parametrize("tc", ["tc-01-perfect", "tc-02-good", "tc-03-medium", "tc-04-simple"])
async def test_pipeline_token_tally_accumulated(tc):
    """Token tally must sum across all 6 agent calls (5 nodes, planning+risk parallel = 6 calls)."""
    orchestrator = PipelineOrchestrator.for_testing()
    uc = _load("use_case", tc); intake = _load("intake", tc)
    plan = _load("planning", tc); risk = _load("risk", tc)
    staffing = _load("staffing", tc); synth = _load("synthesis", tc)

    with (
        patch("agent.orchestrator.UseCaseAgent")  as MockUC,
        patch("agent.orchestrator.IntakeAgent")   as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent")     as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        MockUC.return_value.run_async    = AsyncMock(return_value=_result(uc))
        MockInt.return_value.run_async   = AsyncMock(return_value=_result(intake))
        MockPlan.return_value.run_async  = AsyncMock(return_value=_result(plan))
        MockRisk.return_value.run_async  = AsyncMock(return_value=_result(risk))
        MockStaff.return_value.run_async = AsyncMock(return_value=_result(staffing))
        MockSynth.return_value.run_async = AsyncMock(return_value=_result(synth))

        result = await orchestrator.run(_brief(tc), f"sess-tok-{tc}", "test-user")

    # 6 agent calls × 500 input tokens each
    assert result.token_tally.input_tokens == 3000
    assert result.token_tally.output_tokens == 1800


@pytest.mark.asyncio
@pytest.mark.parametrize("tc", ["tc-01-perfect", "tc-02-good", "tc-03-medium", "tc-04-simple"])
async def test_pipeline_report_passes_schema_validation(tc):
    """
    Assembled report must have no STRUCTURAL errors (missing keys, wrong types).

    P2-era soft business rules (e.g. assumption count thresholds, urgency wording)
    may legitimately differ in P3 since agents reason independently. We filter those
    out and only fail on structural issues that would break the frontend.
    """
    report = await _run_pipeline(tc)
    result = _VALIDATOR.validate(dict(report))
    # Structural errors: missing fields, null where not allowed, type mismatches
    structural_errors = [
        e for e in result.get("errors", [])
        if any(kw in e.lower() for kw in ("missing", "required", "null", "none", "type", "key"))
    ]
    assert not structural_errors, (
        f"{tc}: structural validation errors: {structural_errors}"
    )
