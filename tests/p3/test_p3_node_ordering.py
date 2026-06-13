"""
tests/p3/test_p3_node_ordering.py

Verifies two things introduced by the planning_node → risk_node split:

1. ORDERING: planning_node completes before risk_node is called.
2. DATA FLOW: risk_node receives the full project_plan_artifact, not an empty dict.

All agents are mocked — no API key required.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from agent.orchestrator import PipelineOrchestrator
from tests.p3.test_orchestrator_pipeline import (
    USE_CASE_ARTIFACT,
    INTAKE_ARTIFACT,
    PROJECT_PLAN_ARTIFACT,
    RISK_ARTIFACT,
    STAFFING_ARTIFACT,
    SYNTHESIS_ARTIFACT,
    _agent_result,
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_result(artifact: dict) -> dict:
    return _agent_result(artifact)


# ── ordering test ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_planning_runs_before_risk():
    """planning_node must complete before risk_node is called."""
    call_order: list[str] = []

    async def fake_planning(context):
        call_order.append("planning")
        return _make_result(PROJECT_PLAN_ARTIFACT)

    async def fake_risk(context):
        call_order.append("risk")
        return _make_result(RISK_ARTIFACT)

    orchestrator = PipelineOrchestrator.for_testing()

    with (
        patch("agent.orchestrator.UseCaseAgent") as MockUC,
        patch("agent.orchestrator.IntakeAgent") as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent") as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        MockUC.return_value.run_async = AsyncMock(return_value=_make_result(USE_CASE_ARTIFACT))
        MockInt.return_value.run_async = AsyncMock(return_value=_make_result(INTAKE_ARTIFACT))
        MockPlan.return_value.run_async = AsyncMock(side_effect=fake_planning)
        MockRisk.return_value.run_async = AsyncMock(side_effect=fake_risk)
        MockStaff.return_value.run_async = AsyncMock(return_value=_make_result(STAFFING_ARTIFACT))
        MockSynth.return_value.run_async = AsyncMock(return_value=_make_result(SYNTHESIS_ARTIFACT))

        await orchestrator.run("brief", "sess-order", "user-1")

    assert call_order == ["planning", "risk"], (
        f"Expected planning before risk, got: {call_order}"
    )


# ── data flow test ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_risk_receives_planning_artifact():
    """risk_node must receive the full project_plan_artifact, not an empty dict."""
    captured_context: dict = {}

    async def fake_risk(context):
        captured_context.update(context)
        return _make_result(RISK_ARTIFACT)

    orchestrator = PipelineOrchestrator.for_testing()

    with (
        patch("agent.orchestrator.UseCaseAgent") as MockUC,
        patch("agent.orchestrator.IntakeAgent") as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent") as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        MockUC.return_value.run_async = AsyncMock(return_value=_make_result(USE_CASE_ARTIFACT))
        MockInt.return_value.run_async = AsyncMock(return_value=_make_result(INTAKE_ARTIFACT))
        MockPlan.return_value.run_async = AsyncMock(return_value=_make_result(PROJECT_PLAN_ARTIFACT))
        MockRisk.return_value.run_async = AsyncMock(side_effect=fake_risk)
        MockStaff.return_value.run_async = AsyncMock(return_value=_make_result(STAFFING_ARTIFACT))
        MockSynth.return_value.run_async = AsyncMock(return_value=_make_result(SYNTHESIS_ARTIFACT))

        await orchestrator.run("brief", "sess-dataflow", "user-1")

    plan_passed = captured_context.get("project_plan", {})
    assert plan_passed, "risk_node received empty project_plan — planning artifact not flowing through"
    assert "project_plan" in plan_passed, (
        f"project_plan key missing from passed artifact: {list(plan_passed.keys())}"
    )


@pytest.mark.asyncio
async def test_risk_receives_wbs_phases():
    """risk_node receives the phases list from the planning artifact."""
    captured_plan: dict = {}

    async def fake_risk(context):
        captured_plan.update(context.get("project_plan", {}))
        return _make_result(RISK_ARTIFACT)

    orchestrator = PipelineOrchestrator.for_testing()

    with (
        patch("agent.orchestrator.UseCaseAgent") as MockUC,
        patch("agent.orchestrator.IntakeAgent") as MockInt,
        patch("agent.orchestrator.PlanningAgent") as MockPlan,
        patch("agent.orchestrator.RiskAgent") as MockRisk,
        patch("agent.orchestrator.StaffingAgent") as MockStaff,
        patch("agent.orchestrator.SynthesisAgent") as MockSynth,
    ):
        MockUC.return_value.run_async = AsyncMock(return_value=_make_result(USE_CASE_ARTIFACT))
        MockInt.return_value.run_async = AsyncMock(return_value=_make_result(INTAKE_ARTIFACT))
        MockPlan.return_value.run_async = AsyncMock(return_value=_make_result(PROJECT_PLAN_ARTIFACT))
        MockRisk.return_value.run_async = AsyncMock(side_effect=fake_risk)
        MockStaff.return_value.run_async = AsyncMock(return_value=_make_result(STAFFING_ARTIFACT))
        MockSynth.return_value.run_async = AsyncMock(return_value=_make_result(SYNTHESIS_ARTIFACT))

        await orchestrator.run("brief", "sess-wbs", "user-1")

    phases = captured_plan.get("project_plan", {}).get("phases", [])
    assert len(phases) > 0, (
        "risk_node received no phases from planning artifact — WBS not flowing through"
    )
