"""
Tests for agent/orchestrator.py — pipeline logic, gate routing, report assembly.

All tests use:
  - PipelineOrchestrator.for_testing()  → MemorySaver, no filesystem
  - unittest.mock.patch on agent classes in agent.orchestrator namespace
  - No real Anthropic API calls
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from agent.orchestrator import (
    PipelineOrchestrator,
    REFINEMENT_TARGETS,
    intake_gate_router,
    _assemble_report,
    _apply_staffing_corrections,
    _merge_questions,
    _gate_reason,
    _build_result,
    PipelineState,
)
from schemas.partial_schemas import PipelineResult, TokenTally


# ---------------------------------------------------------------------------
# Fixtures — minimal valid artifacts for each agent
# ---------------------------------------------------------------------------

USE_CASE_ARTIFACT = {
    "system_boundary": "Expense Portal",
    "actors": [
        {"id": "A1", "name": "Employee", "type": "primary"},
        {"id": "A2", "name": "Manager", "type": "primary"},
    ],
    "use_cases": [
        {"id": "UC1", "name": "Submit Expense", "actors": ["A1"], "complexity": "simple"},
        {"id": "UC2", "name": "Approve Expense", "actors": ["A2"], "complexity": "simple"},
    ],
    "relationships": [],
    "input_quality_signal": "HIGH",
    "anti_patterns_detected": [],
}

INTAKE_ARTIFACT = {
    "project_understanding": {"primary_goal": "Replace spreadsheet expense process"},
    "assumption_log": [],
    "report_metadata": {
        "project_type": "TYPE_B",
        "sdlc_approach": "Waterfall",
        "input_quality": "HIGH",
    },
    "constraints": {
        "hard": {"deadline": "10 weeks", "budget": "$28,000"},
        "soft": {},
        "nfr": {},
    },
    "open_questions_pre_planning": [],
}

PROJECT_PLAN_ARTIFACT = {
    "project_plan": {
        "total_duration_weeks": 10.0,
        "phases": [
            {"phase_number": 1, "name": "Discovery", "duration_weeks": 1.0,
             "tasks": [{"id": "T1", "name": "Requirements", "effort_hours": 8.0,
                        "owner_role": "PM", "critical_path": True, "slack_days": 0,
                        "dependencies": [], "risk_flag": False,
                        "definition_of_done": "Approved"}]},
        ],
    },
    "use_case_task_mapping": {"UC1": ["T1"], "UC2": ["T2"]},
}

RISK_ARTIFACT = {
    "risk_register": [
        {"id": "R1", "category": "Resource", "description": "Developer availability",
         "probability": "LOW", "impact": "HIGH", "score": "HIGH",
         "trigger": "Developer leave", "mitigation": "Contractor backup",
         "contingency": "Extend timeline"},
    ],
    "risk_use_case_mapping": {"R1": ["UC1"]},
    "critical_path_risk_flags": ["T1"],
}

STAFFING_ARTIFACT = {
    "staffing_plan": [
        {"role": "Full-Stack Developer", "phase_involvement": [1, 2, 3],
         "total_hours": 320.0, "allocation_percent": 100.0,
         "skills_required": ["React", "Node.js", "PostgreSQL"],
         "critical_path": True, "notes": ""},
        {"role": "PM", "phase_involvement": [1, 2, 3, 4],
         "total_hours": 80.0, "allocation_percent": 50.0,
         "skills_required": ["Stakeholder management"],
         "critical_path": False, "notes": ""},
    ],
    "open_questions": [
        {"priority": 1, "question": "Is SendGrid quota confirmed?",
         "urgency": "Before build", "impact_if_unanswered": "Email notifications blocked"},
    ],
    "pm_confidence_score": {"score": 80.0, "deductions": [], "interpretation": "PM confidence score is 80.0."},
    "project_viability": {"viable": True, "viability_score": 85},
    "actor_role_mapping": {"A1": ["Full-Stack Developer"], "A2": ["PM"]},
}

SYNTHESIS_ARTIFACT = {
    "consistency_issues": [],
    "corrections_applied": [],
    "staffing_corrections": [],
    "added_open_questions": [],
    "pm_confidence_score": {
        "score": 80.0,
        "deductions": [],
        "interpretation": "PM confidence score is 80.0 because no deductions.",
    },
}

TOKENS = {
    "input_tokens": 500,
    "output_tokens": 300,
    "cache_read_tokens": 0,
    "cache_creation_tokens": 0,
    "parse_failed": False,
    "attempts": 1,
    "raw_output": "",
}


def _agent_result(artifact: dict) -> dict:
    return {"artifact": artifact, **TOKENS}


# ---------------------------------------------------------------------------
# intake_gate_router
# ---------------------------------------------------------------------------

def _state(**overrides) -> dict:
    base: dict = {
        "raw_brief": "brief",
        "session_id": "s1",
        "user_id": "u1",
        "use_case_artifact": dict(USE_CASE_ARTIFACT),
        "intake_artifact": dict(INTAKE_ARTIFACT),
        "project_plan_artifact": {},
        "risk_register_artifact": {},
        "staffing_plan_artifact": {},
        "synthesis_artifact": {},
        "token_tally": {},
        "refinement_section": None,
        "refinement_feedback": None,
    }
    base.update(overrides)
    return base


def test_gate_router_high_quality_few_assumptions_continues():
    s = _state()
    assert intake_gate_router(s) == "continue"


def test_gate_router_low_quality_fires():
    s = _state(use_case_artifact={**USE_CASE_ARTIFACT, "input_quality_signal": "LOW"})
    assert intake_gate_router(s) == "gate_end"


def test_gate_router_many_assumptions_continues():
    many = [{"id": f"A{i}"} for i in range(10)]
    s = _state(intake_artifact={**INTAKE_ARTIFACT, "assumption_log": many})
    assert intake_gate_router(s) == "continue"


def test_gate_router_medium_quality_continues():
    s = _state(use_case_artifact={**USE_CASE_ARTIFACT, "input_quality_signal": "MEDIUM"})
    assert intake_gate_router(s) == "continue"


# ---------------------------------------------------------------------------
# _gate_reason
# ---------------------------------------------------------------------------

def test_gate_reason_low_quality():
    reason = _gate_reason("LOW")
    assert "LOW" in reason


def test_gate_reason_fallback_text():
    reason = _gate_reason("")
    assert "Gate triggered" in reason


# ---------------------------------------------------------------------------
# _apply_staffing_corrections
# ---------------------------------------------------------------------------

def test_apply_add_role_appends_row():
    plan = [{"role": "Dev", "critical_path": False}]
    corrections = [{"action": "add_role", "role": "Designer", "total_hours": 40.0}]
    result = _apply_staffing_corrections(plan, corrections)
    assert len(result) == 2
    assert result[1]["role"] == "Designer"
    assert "action" not in result[1]


def test_apply_set_critical_path_updates_existing_role():
    plan = [{"role": "Backend Developer", "critical_path": False}]
    corrections = [{"action": "set_critical_path", "role": "Backend Developer"}]
    result = _apply_staffing_corrections(plan, corrections)
    assert result[0]["critical_path"] is True


def test_apply_set_critical_path_unknown_role_noop():
    plan = [{"role": "Dev", "critical_path": False}]
    corrections = [{"action": "set_critical_path", "role": "NonExistent"}]
    result = _apply_staffing_corrections(plan, corrections)
    assert result[0]["critical_path"] is False


def test_apply_empty_corrections_unchanged():
    plan = [{"role": "Dev"}]
    result = _apply_staffing_corrections(plan, [])
    assert result == plan


def test_apply_does_not_mutate_original():
    original = [{"role": "Dev", "critical_path": False}]
    _apply_staffing_corrections(original, [{"action": "set_critical_path", "role": "Dev"}])
    assert original[0]["critical_path"] is False  # original untouched


# ---------------------------------------------------------------------------
# _merge_questions
# ---------------------------------------------------------------------------

def test_merge_questions_combines_lists():
    staffing = {"open_questions": [{"question": "Q1"}]}
    synthesis = {"added_open_questions": [{"question": "Q2"}]}
    merged = _merge_questions(staffing, synthesis)
    assert len(merged) == 2
    assert merged[0]["question"] == "Q1"
    assert merged[1]["question"] == "Q2"


def test_merge_questions_empty_synthesis():
    staffing = {"open_questions": [{"question": "Q1"}]}
    synthesis = {}
    merged = _merge_questions(staffing, synthesis)
    assert merged == [{"question": "Q1"}]


def test_merge_questions_both_empty():
    assert _merge_questions({}, {}) == []


# ---------------------------------------------------------------------------
# _assemble_report
# ---------------------------------------------------------------------------

def _full_state() -> dict:
    return _state(
        use_case_artifact=USE_CASE_ARTIFACT,
        intake_artifact=INTAKE_ARTIFACT,
        project_plan_artifact=PROJECT_PLAN_ARTIFACT,
        risk_register_artifact=RISK_ARTIFACT,
        staffing_plan_artifact=STAFFING_ARTIFACT,
        synthesis_artifact=SYNTHESIS_ARTIFACT,
    )


def test_assemble_report_has_required_keys():
    report = _assemble_report(_full_state())
    required = [
        "project_understanding", "assumption_log", "open_questions",
        "report_metadata", "use_case_model", "project_plan",
        "use_case_task_mapping", "risk_register", "risk_use_case_mapping",
        "critical_path_risk_flags", "staffing_plan", "actor_role_mapping",
        "project_viability", "pm_confidence_score",
    ]
    for key in required:
        assert key in report, f"Missing key: {key}"


def test_assemble_report_applies_staffing_corrections():
    synthesis = {
        **SYNTHESIS_ARTIFACT,
        "staffing_corrections": [{"action": "add_role", "role": "QA Engineer", "total_hours": 60.0}],
    }
    state = _full_state()
    state["synthesis_artifact"] = synthesis
    report = _assemble_report(state)
    roles = [r["role"] for r in report["staffing_plan"]]
    assert "QA Engineer" in roles


def test_assemble_report_merges_questions():
    synthesis = {
        **SYNTHESIS_ARTIFACT,
        "added_open_questions": [{"priority": 2, "question": "Added by synthesis"}],
    }
    state = _full_state()
    state["synthesis_artifact"] = synthesis
    report = _assemble_report(state)
    questions = [q["question"] for q in report["open_questions"]]
    assert "Is SendGrid quota confirmed?" in questions
    assert "Added by synthesis" in questions


def test_assemble_report_pm_confidence_from_synthesis():
    state = _full_state()
    report = _assemble_report(state)
    assert report["pm_confidence_score"]["score"] == 80.0


# ---------------------------------------------------------------------------
# _build_result
# ---------------------------------------------------------------------------

def _make_state_for_result(**overrides):
    base = _full_state()
    base.update(overrides)
    return base


def test_build_result_success_path():
    state = _make_state_for_result()
    result = _build_result(state)
    assert result.succeeded
    assert result.final_report is not None
    assert result.paused_at is None


def test_build_result_gate_path_empty_plan():
    state = _make_state_for_result(project_plan_artifact={}, synthesis_artifact={})
    result = _build_result(state)
    assert not result.succeeded
    assert result.paused_at == "intake"
    assert result.gate_signal is not None


def test_build_result_synthesis_parse_error():
    state = _make_state_for_result(synthesis_artifact={"parse_error": True})
    result = _build_result(state)
    assert not result.succeeded
    assert result.paused_at == "intake"


def test_build_result_token_tally_accumulated():
    state = _make_state_for_result(token_tally={
        "input_tokens": 1000,
        "output_tokens": 500,
        "cache_read_tokens": 200,
        "cache_creation_tokens": 100,
    })
    result = _build_result(state)
    assert result.token_tally.input_tokens == 1000
    assert result.token_tally.output_tokens == 500


def test_build_result_partial_artifacts_always_present():
    state = _make_state_for_result(project_plan_artifact={})
    result = _build_result(state)
    assert "use_case_artifact" in result.partial_artifacts
    assert "intake_artifact" in result.partial_artifacts


# ---------------------------------------------------------------------------
# Integration: happy-path pipeline (all agents mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_pipeline_happy_path():
    orchestrator = PipelineOrchestrator.for_testing()
    with (
        patch("agent.orchestrator.UseCaseAgent") as MockUC,
        patch("agent.orchestrator.IntakeAgent") as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent") as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        MockUC.return_value.run_async = AsyncMock(return_value=_agent_result(USE_CASE_ARTIFACT))
        MockInt.return_value.run_async = AsyncMock(return_value=_agent_result(INTAKE_ARTIFACT))
        MockPlan.return_value.run_async = AsyncMock(return_value=_agent_result(PROJECT_PLAN_ARTIFACT))
        MockRisk.return_value.run_async = AsyncMock(return_value=_agent_result(RISK_ARTIFACT))
        MockStaff.return_value.run_async = AsyncMock(return_value=_agent_result(STAFFING_ARTIFACT))
        MockSynth.return_value.run_async = AsyncMock(return_value=_agent_result(SYNTHESIS_ARTIFACT))

        result = await orchestrator.run("test brief", "session-1", "user-1")

    assert result.succeeded
    assert result.final_report is not None
    assert "project_plan" in result.final_report
    assert "risk_register" in result.final_report
    assert "staffing_plan" in result.final_report
    assert result.paused_at is None


@pytest.mark.asyncio
async def test_full_pipeline_accumulates_tokens():
    orchestrator = PipelineOrchestrator.for_testing()
    with (
        patch("agent.orchestrator.UseCaseAgent") as MockUC,
        patch("agent.orchestrator.IntakeAgent") as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent") as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        MockUC.return_value.run_async = AsyncMock(return_value=_agent_result(USE_CASE_ARTIFACT))
        MockInt.return_value.run_async = AsyncMock(return_value=_agent_result(INTAKE_ARTIFACT))
        MockPlan.return_value.run_async = AsyncMock(return_value=_agent_result(PROJECT_PLAN_ARTIFACT))
        MockRisk.return_value.run_async = AsyncMock(return_value=_agent_result(RISK_ARTIFACT))
        MockStaff.return_value.run_async = AsyncMock(return_value=_agent_result(STAFFING_ARTIFACT))
        MockSynth.return_value.run_async = AsyncMock(return_value=_agent_result(SYNTHESIS_ARTIFACT))

        result = await orchestrator.run("test brief", "session-tok", "user-1")

    # 5 node calls × 500 input tokens each = 2500 (planning + risk run in parallel = 2 calls)
    # use_case(500) + intake(500) + planning(500) + risk(500) + staffing(500) + synthesis(500) = 3000
    assert result.token_tally.input_tokens == 3000
    assert result.token_tally.output_tokens == 1800  # 6 × 300


@pytest.mark.asyncio
async def test_gate_fires_when_low_quality():
    orchestrator = PipelineOrchestrator.for_testing()
    low_quality_uc = {**USE_CASE_ARTIFACT, "input_quality_signal": "LOW"}
    with (
        patch("agent.orchestrator.UseCaseAgent") as MockUC,
        patch("agent.orchestrator.IntakeAgent") as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
    ):
        MockUC.return_value.run_async = AsyncMock(return_value=_agent_result(low_quality_uc))
        MockInt.return_value.run_async = AsyncMock(return_value=_agent_result(INTAKE_ARTIFACT))
        MockPlan.return_value.run_async = AsyncMock(return_value=_agent_result(PROJECT_PLAN_ARTIFACT))

        result = await orchestrator.run("test brief", "session-gate", "user-1")

    assert not result.succeeded
    assert result.paused_at == "intake"
    assert "LOW" in result.gate_signal
    MockPlan.return_value.run_async.assert_not_called()


@pytest.mark.asyncio
async def test_many_assumptions_does_not_fire_gate():
    orchestrator = PipelineOrchestrator.for_testing()
    many_assumptions = [{"id": f"A{i}", "what": "assumption"} for i in range(10)]
    intake_with_many = {**INTAKE_ARTIFACT, "assumption_log": many_assumptions}

    with (
        patch("agent.orchestrator.UseCaseAgent") as MockUC,
        patch("agent.orchestrator.IntakeAgent") as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent") as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        MockUC.return_value.run_async = AsyncMock(return_value=_agent_result(USE_CASE_ARTIFACT))
        MockInt.return_value.run_async = AsyncMock(return_value=_agent_result(intake_with_many))
        MockPlan.return_value.run_async = AsyncMock(return_value=_agent_result(PROJECT_PLAN_ARTIFACT))
        MockRisk.return_value.run_async = AsyncMock(return_value=_agent_result(RISK_ARTIFACT))
        MockStaff.return_value.run_async = AsyncMock(return_value=_agent_result(STAFFING_ARTIFACT))
        MockSynth.return_value.run_async = AsyncMock(return_value=_agent_result(SYNTHESIS_ARTIFACT))

        result = await orchestrator.run("test brief", "session-gate2", "user-1")

    assert result.succeeded
    MockPlan.return_value.run_async.assert_called_once()


@pytest.mark.asyncio
async def test_partial_artifacts_available_after_gate():
    orchestrator = PipelineOrchestrator.for_testing()
    low_quality_uc = {**USE_CASE_ARTIFACT, "input_quality_signal": "LOW"}

    with (
        patch("agent.orchestrator.UseCaseAgent") as MockUC,
        patch("agent.orchestrator.IntakeAgent") as MockInt,
    ):
        MockUC.return_value.run_async = AsyncMock(return_value=_agent_result(low_quality_uc))
        MockInt.return_value.run_async = AsyncMock(return_value=_agent_result(INTAKE_ARTIFACT))

        result = await orchestrator.run("test brief", "session-partial", "user-1")

    assert result.partial_artifacts["use_case_artifact"]["input_quality_signal"] == "LOW"
    assert result.partial_artifacts["intake_artifact"]["report_metadata"]["project_type"] == "TYPE_B"
