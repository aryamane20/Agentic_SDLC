"""
Tests for P3 refinement routing in agent/orchestrator.py.

Verifies that each feedback section routes to the correct as_node so that
only the affected agents re-run (targeted refinement, not full re-run).
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, call

from agent.orchestrator import (
    PipelineOrchestrator,
    REFINEMENT_TARGETS,
)

# All valid node names in the graph
_VALID_NODES = {"use_case_node", "intake_node", "planning_risk_node", "staffing_node", "synthesis_node"}

# For each section, which nodes MUST re-run (downstream from the as_node)
_EXPECTED_RERUNS = {
    "pm_confidence_score":   ["synthesis_node"],
    "staffing_plan":         ["staffing_node", "synthesis_node"],
    "open_questions":        ["staffing_node", "synthesis_node"],
    "risk_register":         ["planning_risk_node", "staffing_node", "synthesis_node"],
    "project_plan":          ["planning_risk_node", "staffing_node", "synthesis_node"],
    "assumption_log":        ["intake_node", "planning_risk_node", "staffing_node", "synthesis_node"],
    "project_understanding": ["intake_node", "planning_risk_node", "staffing_node", "synthesis_node"],
}

# Graph successor map: as_node X → nodes that will re-run after X
_SUCCESSORS = {
    "use_case_node":       ["intake_node", "planning_risk_node", "staffing_node", "synthesis_node"],
    "intake_node":         ["planning_risk_node", "staffing_node", "synthesis_node"],
    "planning_risk_node":  ["staffing_node", "synthesis_node"],
    "staffing_node":       ["synthesis_node"],
    "synthesis_node":      [],
}


# ---------------------------------------------------------------------------
# REFINEMENT_TARGETS table correctness
# ---------------------------------------------------------------------------

def test_all_sections_present():
    expected_sections = {
        "pm_confidence_score", "staffing_plan", "open_questions",
        "risk_register", "project_plan", "assumption_log", "project_understanding",
    }
    assert set(REFINEMENT_TARGETS.keys()) == expected_sections


def test_all_as_nodes_are_valid_graph_nodes():
    for section, as_node in REFINEMENT_TARGETS.items():
        assert as_node in _VALID_NODES, f"Section '{section}' maps to invalid node '{as_node}'"


@pytest.mark.parametrize("section,expected_reruns", list(_EXPECTED_RERUNS.items()))
def test_section_reruns_correct_nodes(section, expected_reruns):
    as_node = REFINEMENT_TARGETS[section]
    actual_reruns = _SUCCESSORS[as_node]
    assert actual_reruns == expected_reruns, (
        f"Section '{section}': as_node='{as_node}' will re-run {actual_reruns}, "
        f"expected {expected_reruns}"
    )


def test_confidence_only_reruns_synthesis():
    as_node = REFINEMENT_TARGETS["pm_confidence_score"]
    reruns = _SUCCESSORS[as_node]
    assert reruns == ["synthesis_node"]


def test_risk_reruns_from_planning_risk():
    as_node = REFINEMENT_TARGETS["risk_register"]
    reruns = _SUCCESSORS[as_node]
    assert "planning_risk_node" in reruns
    assert "staffing_node" in reruns
    assert "synthesis_node" in reruns


def test_assumption_log_reruns_all_downstream():
    as_node = REFINEMENT_TARGETS["assumption_log"]
    reruns = _SUCCESSORS[as_node]
    assert reruns == ["intake_node", "planning_risk_node", "staffing_node", "synthesis_node"]


def test_refinement_targets_are_not_synthesis_node_itself():
    for section, as_node in REFINEMENT_TARGETS.items():
        assert as_node != "synthesis_node", (
            f"Section '{section}' maps to synthesis_node as as_node — "
            "synthesis_node has no successors, nothing would re-run"
        )


# ---------------------------------------------------------------------------
# Integration: refine() calls aupdate_state with correct as_node
# ---------------------------------------------------------------------------

# Stub artifacts passed to refine() as current_artifacts
_CURRENT_ARTIFACTS = {
    "use_case_artifact": {"input_quality_signal": "HIGH"},
    "intake_artifact": {"assumption_log": [], "report_metadata": {"project_type": "TYPE_B", "sdlc_approach": "Waterfall"}},
    "project_plan_artifact": {"project_plan": {"total_duration_weeks": 10.0}, "use_case_task_mapping": {}},
    "risk_register_artifact": {"risk_register": [], "risk_use_case_mapping": {}, "critical_path_risk_flags": []},
    "staffing_plan_artifact": {
        "staffing_plan": [{"role": "Developer", "critical_path": False}],
        "open_questions": [],
        "pm_confidence_score": {"score": 75.0, "deductions": [], "interpretation": "score is 75.0"},
        "project_viability": {"viable": True},
        "actor_role_mapping": {},
    },
    "synthesis_artifact": {
        "consistency_issues": [],
        "corrections_applied": [],
        "staffing_corrections": [],
        "added_open_questions": [],
        "pm_confidence_score": {"score": 75.0, "deductions": [], "interpretation": "score is 75.0"},
    },
}

_SYNTHESIS_RESULT = {
    "artifact": {
        "consistency_issues": [],
        "corrections_applied": ["Refined."],
        "staffing_corrections": [],
        "added_open_questions": [],
        "pm_confidence_score": {"score": 75.0, "deductions": [], "interpretation": "score is 75.0"},
    },
    "input_tokens": 500, "output_tokens": 200,
    "cache_read_tokens": 0, "cache_creation_tokens": 0,
    "parse_failed": False, "attempts": 1, "raw_output": "",
}

_STAFFING_RESULT = {
    "artifact": _CURRENT_ARTIFACTS["staffing_plan_artifact"],
    "input_tokens": 400, "output_tokens": 150,
    "cache_read_tokens": 0, "cache_creation_tokens": 0,
    "parse_failed": False, "attempts": 1, "raw_output": "",
}

_PLANNING_RESULT = {
    "artifact": _CURRENT_ARTIFACTS["project_plan_artifact"],
    "input_tokens": 600, "output_tokens": 250,
    "cache_read_tokens": 0, "cache_creation_tokens": 0,
    "parse_failed": False, "attempts": 1, "raw_output": "",
}

_RISK_RESULT = {
    "artifact": _CURRENT_ARTIFACTS["risk_register_artifact"],
    "input_tokens": 450, "output_tokens": 180,
    "cache_read_tokens": 0, "cache_creation_tokens": 0,
    "parse_failed": False, "attempts": 1, "raw_output": "",
}


@pytest.mark.asyncio
async def test_refine_pm_confidence_only_reruns_synthesis():
    orchestrator = PipelineOrchestrator.for_testing()

    # Pre-seed state so graph has prior checkpoint
    with (
        patch("agent.orchestrator.UseCaseAgent") as MockUC,
        patch("agent.orchestrator.IntakeAgent") as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent") as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        _seed_happy_path(MockUC, MockInt, MockPlan, MockRisk, MockStaff, MockSynth)
        await orchestrator.run("brief", "sess-refine", "user-1")

        # Now refine pm_confidence_score — only synthesis should re-run
        MockSynth.return_value.run_async = AsyncMock(return_value=_SYNTHESIS_RESULT)
        MockStaff.return_value.run_async = AsyncMock(return_value=_STAFFING_RESULT)

        result = await orchestrator.refine(
            section="pm_confidence_score",
            feedback="Recalculate using latest risk counts",
            session_id="sess-refine",
            user_id="user-1",
            current_artifacts=_CURRENT_ARTIFACTS,
        )

    assert result.succeeded
    # Staffing should NOT have re-run during refine
    MockStaff.return_value.run_async.assert_not_called()
    # Synthesis DID re-run
    MockSynth.return_value.run_async.assert_called_once()


@pytest.mark.asyncio
async def test_refine_risk_reruns_planning_and_downstream():
    orchestrator = PipelineOrchestrator.for_testing()

    with (
        patch("agent.orchestrator.UseCaseAgent") as MockUC,
        patch("agent.orchestrator.IntakeAgent") as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent") as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        _seed_happy_path(MockUC, MockInt, MockPlan, MockRisk, MockStaff, MockSynth)
        await orchestrator.run("brief", "sess-risk-refine", "user-1")

        # Reset call counts for refine assertions
        MockPlan.return_value.run_async = AsyncMock(return_value=_PLANNING_RESULT)
        MockRisk.return_value.run_async = AsyncMock(return_value=_RISK_RESULT)
        MockStaff.return_value.run_async = AsyncMock(return_value=_STAFFING_RESULT)
        MockSynth.return_value.run_async = AsyncMock(return_value=_SYNTHESIS_RESULT)
        MockInt.return_value.run_async = AsyncMock(return_value={
            "artifact": _CURRENT_ARTIFACTS["intake_artifact"],
            "input_tokens": 0, "output_tokens": 0,
            "cache_read_tokens": 0, "cache_creation_tokens": 0,
            "parse_failed": False, "attempts": 1, "raw_output": "",
        })

        result = await orchestrator.refine(
            section="risk_register",
            feedback="Add data migration risk",
            session_id="sess-risk-refine",
            user_id="user-1",
            current_artifacts=_CURRENT_ARTIFACTS,
        )

    assert result.succeeded
    MockPlan.return_value.run_async.assert_called_once()
    MockRisk.return_value.run_async.assert_called_once()
    MockStaff.return_value.run_async.assert_called_once()
    MockSynth.return_value.run_async.assert_called_once()
    MockInt.return_value.run_async.assert_not_called()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _seed_happy_path(MockUC, MockInt, MockPlan, MockRisk, MockStaff, MockSynth):
    from tests.p3.test_orchestrator_pipeline import (
        USE_CASE_ARTIFACT, INTAKE_ARTIFACT, PROJECT_PLAN_ARTIFACT,
        RISK_ARTIFACT, STAFFING_ARTIFACT, SYNTHESIS_ARTIFACT, _agent_result,
    )
    MockUC.return_value.run_async = AsyncMock(return_value=_agent_result(USE_CASE_ARTIFACT))
    MockInt.return_value.run_async = AsyncMock(return_value=_agent_result(INTAKE_ARTIFACT))
    MockPlan.return_value.run_async = AsyncMock(return_value=_agent_result(PROJECT_PLAN_ARTIFACT))
    MockRisk.return_value.run_async = AsyncMock(return_value=_agent_result(RISK_ARTIFACT))
    MockStaff.return_value.run_async = AsyncMock(return_value=_agent_result(STAFFING_ARTIFACT))
    MockSynth.return_value.run_async = AsyncMock(return_value=_agent_result(SYNTHESIS_ARTIFACT))
