import json
from pathlib import Path

from agent.base_agent import BaseAgent, MODEL_HAIKU

_PROMPT = Path(__file__).parent.parent.parent / "prompts/agents/risk_v1.6.txt"


class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="risk",
            prompt_path=_PROMPT,
            model=MODEL_HAIKU,
            max_tokens=5000,
        )

    def _is_valid_artifact(self, parsed: dict) -> bool:
        return isinstance(parsed, dict) and "risk_register" in parsed

    def _build_user_message(self, context: dict) -> str:
        brief = context.get("structured_brief", {})
        use_case = context.get("use_case_model", {})
        plan = context.get("project_plan", {})

        # Only pass plan summary (phases + critical path) to avoid ballooning context
        plan_summary = {
            "project_type": brief.get("report_metadata", {}).get("project_type"),
            "total_duration_weeks": plan.get("project_plan", {}).get("total_duration_weeks"),
            "critical_path_summary": plan.get("project_plan", {}).get("critical_path_summary"),
            "use_case_task_mapping": plan.get("use_case_task_mapping", {}),
        }

        brief_compact = json.dumps(brief, separators=(",", ":"))
        uc_compact = json.dumps(use_case, separators=(",", ":"))
        plan_compact = json.dumps(plan_summary, separators=(",", ":"))

        return (
            f"STRUCTURED BRIEF (from Intake Agent):\n{brief_compact}\n\n"
            f"USE CASE MODEL:\n{uc_compact}\n\n"
            f"PROJECT PLAN SUMMARY (from Planning Agent):\n{plan_compact}\n\n"
            "Run Step 7. Output RiskRegisterArtifact JSON only. No prose. No markdown."
        )
