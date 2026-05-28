"""
agent/orchestrator.py

LangGraph StateGraph orchestrator for the P3 multi-agent pipeline.

Graph topology:
    START
      → use_case_node
      → intake_node ──(gate?)──→ planning_risk_node → staffing_node → synthesis_node → END
                     └──────────────────────────────────────────────────────────────→ END

Gate fires if: intake quality == LOW

Refinement: aupdate_state(as_node=X) rewinds the graph to after node X,
then ainvoke(None) continues from X's successor.

Checkpointing: AsyncSqliteSaver at sessions/p3_checkpoints.db.
Tests use MemorySaver (no filesystem) via PipelineOrchestrator.for_testing().
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph, START, END

from agent.agents.use_case_agent import UseCaseAgent
from agent.agents.intake_agent import IntakeAgent
from agent.agents.planning_agent import PlanningAgent
from agent.agents.risk_agent import RiskAgent
from agent.agents.staffing_agent import StaffingAgent
from agent.agents.synthesis_agent import SynthesisAgent
from agent.pm_confidence import (
    compute_confidence,
    extract_confidence_inputs,
    patch_synthesis_artifact,
)
from agent.rag_client import KBRetriever
from schemas.partial_schemas import PipelineResult, TokenTally

_DB_PATH = Path(__file__).parent.parent / "sessions" / "p3_checkpoints.db"

# Maps feedback section name → as_node for aupdate_state.
# "as_node=X" means: act as if X just ran; graph resumes from X's successor.
REFINEMENT_TARGETS: Dict[str, str] = {
    "pm_confidence_score":    "staffing_node",       # re-run synthesis only
    "staffing_plan":          "planning_risk_node",   # re-run staffing → synthesis
    "open_questions":         "planning_risk_node",   # re-run staffing → synthesis
    "risk_register":          "intake_node",          # re-run planning_risk → staffing → synthesis
    "project_plan":           "intake_node",          # re-run planning_risk → staffing → synthesis
    "assumption_log":         "use_case_node",        # re-run intake → all downstream
    "project_understanding":  "use_case_node",        # re-run intake → all downstream
}

_kb = KBRetriever()


# ---------------------------------------------------------------------------
# LangGraph State
# ---------------------------------------------------------------------------

class PipelineState(TypedDict):
    raw_brief: str
    session_id: str
    user_id: str
    # intermediate artifacts
    use_case_artifact: dict       # produced by use_case_node
    intake_artifact: dict         # produced by intake_node
    project_plan_artifact: dict   # produced by planning_risk_node
    risk_register_artifact: dict  # produced by planning_risk_node
    staffing_plan_artifact: dict  # produced by staffing_node
    synthesis_artifact: dict      # produced by synthesis_node
    # cumulative token counts across all agent calls
    token_tally: dict
    # refinement context (None on first run, set by refine())
    refinement_section: Optional[str]
    refinement_feedback: Optional[str]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

async def use_case_node(state: PipelineState) -> dict:
    agent = UseCaseAgent()
    result = await agent.run_async(context={"raw_brief": state["raw_brief"]})
    tally = _copy_tally(state)
    _add_tokens(tally, result)
    return {"use_case_artifact": result["artifact"], "token_tally": tally}


async def intake_node(state: PipelineState) -> dict:
    agent = IntakeAgent()
    context: Dict[str, Any] = {
        "raw_brief": state["raw_brief"],
        "use_case_model": state.get("use_case_artifact") or {},
    }
    result = await agent.run_async(context=context)
    tally = _copy_tally(state)
    _add_tokens(tally, result)
    return {"intake_artifact": result["artifact"], "token_tally": tally}


async def planning_risk_node(state: PipelineState) -> dict:
    planning_agent = PlanningAgent()
    risk_agent = RiskAgent()
    brief = state.get("intake_artifact") or {}
    uc = state.get("use_case_artifact") or {}
    project_type = brief.get("report_metadata", {}).get("project_type")

    planning_ctx: Dict[str, Any] = {
        "structured_brief": brief,
        "use_case_model": uc,
        "_kb_content": _kb.get_for_agent("planning", project_type=project_type),
    }
    risk_ctx: Dict[str, Any] = {
        "structured_brief": brief,
        "use_case_model": uc,
        "project_plan": {},
        "_kb_content": _kb.get_for_agent("risk", project_type=project_type),
    }

    planning_result, risk_result = await asyncio.gather(
        planning_agent.run_async(context=planning_ctx),
        risk_agent.run_async(context=risk_ctx),
    )

    tally = _copy_tally(state)
    _add_tokens(tally, planning_result)
    _add_tokens(tally, risk_result)
    return {
        "project_plan_artifact": planning_result["artifact"],
        "risk_register_artifact": risk_result["artifact"],
        "token_tally": tally,
    }


async def staffing_node(state: PipelineState) -> dict:
    agent = StaffingAgent()
    brief = state.get("intake_artifact") or {}
    project_type = brief.get("report_metadata", {}).get("project_type")
    context: Dict[str, Any] = {
        "structured_brief": brief,
        "use_case_model": state.get("use_case_artifact") or {},
        "project_plan": state.get("project_plan_artifact") or {},
        "risk_register_artifact": state.get("risk_register_artifact") or {},
        "_kb_content": _kb.get_for_agent("staffing", project_type=project_type),
    }
    result = await agent.run_async(context=context)
    tally = _copy_tally(state)
    _add_tokens(tally, result)
    return {"staffing_plan_artifact": result["artifact"], "token_tally": tally}


async def synthesis_node(state: PipelineState) -> dict:
    agent = SynthesisAgent()
    context: Dict[str, Any] = {
        "use_case_model": state.get("use_case_artifact") or {},
        "structured_brief": state.get("intake_artifact") or {},
        "project_plan": state.get("project_plan_artifact") or {},
        "risk_register_artifact": state.get("risk_register_artifact") or {},
        "staffing_plan_artifact": state.get("staffing_plan_artifact") or {},
    }
    result = await agent.run_async(context=context)
    artifact = result["artifact"]

    # Replace LLM's unreliable arithmetic with deterministic Python computation
    try:
        ci = extract_confidence_inputs(
            use_case_artifact=state.get("use_case_artifact") or {},
            intake_artifact=state.get("intake_artifact") or {},
            risk_artifact=state.get("risk_register_artifact") or {},
            planning_artifact=state.get("project_plan_artifact") or {},
        )
        confidence_result = compute_confidence(**ci)
        artifact = patch_synthesis_artifact(artifact, confidence_result)
    except Exception:
        pass

    tally = _copy_tally(state)
    _add_tokens(tally, result)
    return {"synthesis_artifact": artifact, "token_tally": tally}


# ---------------------------------------------------------------------------
# Conditional edge (gate after intake)
# ---------------------------------------------------------------------------

def intake_gate_router(state: PipelineState) -> str:
    uc = state.get("use_case_artifact") or {}
    quality = uc.get("input_quality_signal")
    if quality == "LOW":
        return "gate_end"
    return "continue"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    g = StateGraph(PipelineState)
    g.add_node("use_case_node", use_case_node)
    g.add_node("intake_node", intake_node)
    g.add_node("planning_risk_node", planning_risk_node)
    g.add_node("staffing_node", staffing_node)
    g.add_node("synthesis_node", synthesis_node)

    g.add_edge(START, "use_case_node")
    g.add_edge("use_case_node", "intake_node")
    g.add_conditional_edges(
        "intake_node",
        intake_gate_router,
        {"continue": "planning_risk_node", "gate_end": END},
    )
    g.add_edge("planning_risk_node", "staffing_node")
    g.add_edge("staffing_node", "synthesis_node")
    g.add_edge("synthesis_node", END)
    return g


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class PipelineOrchestrator:
    """
    Wraps the compiled LangGraph app with lifecycle management.

    Typical service usage:
        orchestrator = PipelineOrchestrator()
        await orchestrator.setup()          # once at startup
        result = await orchestrator.run(...)
        await orchestrator.teardown()       # once at shutdown

    Test usage:
        orchestrator = PipelineOrchestrator.for_testing()
        # no setup() needed — uses in-memory MemorySaver
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or _DB_PATH
        self._conn: Optional[aiosqlite.Connection] = None
        self._app = None

    @classmethod
    def for_testing(cls, checkpointer=None) -> "PipelineOrchestrator":
        from langgraph.checkpoint.memory import MemorySaver
        inst = cls.__new__(cls)
        inst._db_path = None
        inst._conn = None
        inst._app = build_graph().compile(checkpointer=checkpointer or MemorySaver())
        return inst

    async def setup(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self._db_path))
        checkpointer = AsyncSqliteSaver(self._conn)
        await checkpointer.setup()
        self._app = build_graph().compile(checkpointer=checkpointer)

    async def teardown(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def run(
        self,
        raw_brief: str,
        session_id: str,
        user_id: str,
    ) -> PipelineResult:
        if self._app is None:
            raise RuntimeError("Call setup() before run()")

        config = _thread_config(user_id, session_id)
        initial: PipelineState = {
            "raw_brief": raw_brief,
            "session_id": session_id,
            "user_id": user_id,
            "use_case_artifact": {},
            "intake_artifact": {},
            "project_plan_artifact": {},
            "risk_register_artifact": {},
            "staffing_plan_artifact": {},
            "synthesis_artifact": {},
            "token_tally": {},
            "refinement_section": None,
            "refinement_feedback": None,
        }
        final_state = await self._app.ainvoke(initial, config)
        return _build_result(final_state)

    async def refine(
        self,
        section: str,
        feedback: str,
        session_id: str,
        user_id: str,
        current_artifacts: Dict[str, Any],
    ) -> PipelineResult:
        if self._app is None:
            raise RuntimeError("Call setup() before refine()")

        as_node = REFINEMENT_TARGETS.get(section, "staffing_node")
        config = _thread_config(user_id, session_id)

        state_update: Dict[str, Any] = {
            **current_artifacts,
            "refinement_section": section,
            "refinement_feedback": feedback,
        }
        await self._app.aupdate_state(config, state_update, as_node=as_node)
        final_state = await self._app.ainvoke(None, config)
        return _build_result(final_state)

    async def delete_run(self, user_id: str, session_id: str) -> None:
        if self._app is None:
            return
        thread_id = f"{user_id}:{session_id}"
        try:
            await self._app.checkpointer.adelete_thread(thread_id)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _thread_config(user_id: str, session_id: str) -> dict:
    return {"configurable": {"thread_id": f"{user_id}:{session_id}"}}


def _copy_tally(state: PipelineState) -> dict:
    return dict(state.get("token_tally") or {})


def _add_tokens(tally: dict, agent_result: dict) -> None:
    for key in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens"):
        tally[key] = tally.get(key, 0) + agent_result.get(key, 0)


def _build_result(state: Dict[str, Any]) -> PipelineResult:
    tally_dict = state.get("token_tally") or {}
    tally = TokenTally(
        input_tokens=tally_dict.get("input_tokens", 0),
        output_tokens=tally_dict.get("output_tokens", 0),
        cache_read_tokens=tally_dict.get("cache_read_tokens", 0),
        cache_creation_tokens=tally_dict.get("cache_creation_tokens", 0),
    )

    partial = {
        "use_case_artifact": state.get("use_case_artifact") or {},
        "intake_artifact": state.get("intake_artifact") or {},
        "project_plan_artifact": state.get("project_plan_artifact") or {},
        "risk_register_artifact": state.get("risk_register_artifact") or {},
        "staffing_plan_artifact": state.get("staffing_plan_artifact") or {},
        "synthesis_artifact": state.get("synthesis_artifact") or {},
    }

    plan = state.get("project_plan_artifact") or {}
    synthesis = state.get("synthesis_artifact") or {}

    if plan and synthesis and not synthesis.get("parse_error"):
        # Full pipeline completed
        final_report = _assemble_report(state)
        corrections = synthesis.get("corrections_applied") or []
        return PipelineResult(
            final_report=final_report,
            synthesis_corrections=corrections,
            partial_artifacts=partial,
            token_tally=tally,
        )

    # Gate fired — planning never ran
    uc = state.get("use_case_artifact") or {}
    quality = uc.get("input_quality_signal", "")
    return PipelineResult(
        paused_at="intake",
        gate_signal=_gate_reason(quality),
        partial_artifacts=partial,
        token_tally=tally,
    )


def _gate_reason(quality: str) -> str:
    if quality == "LOW":
        return "Gate triggered: input quality is LOW"
    return "Gate triggered: intake quality check failed"


def _assemble_report(state: Dict[str, Any]) -> Dict[str, Any]:
    """Merge all 5 agent artifacts into the final PMReport shape."""
    brief = state.get("intake_artifact") or {}
    uc = state.get("use_case_artifact") or {}
    plan = state.get("project_plan_artifact") or {}
    risk = state.get("risk_register_artifact") or {}
    staffing = state.get("staffing_plan_artifact") or {}
    synthesis = state.get("synthesis_artifact") or {}

    report: Dict[str, Any] = {
        "project_understanding":    brief.get("project_understanding", {}),
        "assumption_log":           brief.get("assumption_log", []),
        "open_questions":           _merge_questions(staffing, synthesis),
        "report_metadata":          brief.get("report_metadata", {}),
        "use_case_model":           uc,
        "project_plan":             plan.get("project_plan", {}),
        "use_case_task_mapping":    plan.get("use_case_task_mapping", {}),
        "risk_register":            risk.get("risk_register", []),
        "risk_use_case_mapping":    risk.get("risk_use_case_mapping", {}),
        "critical_path_risk_flags": risk.get("critical_path_risk_flags", []),
        "staffing_plan":            _apply_staffing_corrections(
            staffing.get("staffing_plan", []),
            synthesis.get("staffing_corrections", []),
        ),
        "actor_role_mapping":       staffing.get("actor_role_mapping", {}),
        "project_viability":        staffing.get("project_viability", {}),
        "pm_confidence_score":      synthesis.get("pm_confidence_score", {}),
    }
    return report


def _merge_questions(staffing: dict, synthesis: dict) -> List[Dict]:
    existing = staffing.get("open_questions") or []
    added = synthesis.get("added_open_questions") or []
    return existing + added


def _apply_staffing_corrections(
    staffing_plan: List[Dict],
    corrections: List[Dict],
) -> List[Dict]:
    plan = [dict(row) for row in staffing_plan]
    for corr in corrections:
        action = corr.get("action")
        if action == "add_role":
            plan.append({k: v for k, v in corr.items() if k != "action"})
        elif action == "set_critical_path":
            role = corr.get("role", "")
            for row in plan:
                if row.get("role") == role:
                    row["critical_path"] = True
    return plan
