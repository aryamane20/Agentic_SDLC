import json
from pathlib import Path

from agent.base_agent import BaseAgent, MODEL_HAIKU

_PROMPT = Path(__file__).parent.parent.parent / "prompts/agents/staffing_v1.0.txt"


class StaffingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="staffing",
            prompt_path=_PROMPT,
            model=MODEL_HAIKU,
            max_tokens=4000,
        )

    def _is_valid_artifact(self, parsed: dict) -> bool:
        return isinstance(parsed, dict) and "staffing_plan" in parsed

    def _build_user_message(self, context: dict) -> str:
        brief = context.get("structured_brief", {})
        use_case = context.get("use_case_model", {})
        plan = context.get("project_plan", {})
        risk = context.get("risk_register_artifact", {})

        brief_compact = json.dumps(brief, separators=(",", ":"))
        uc_compact = json.dumps(use_case, separators=(",", ":"))
        plan_compact = json.dumps(plan, separators=(",", ":"))
        risk_compact = json.dumps(risk, separators=(",", ":"))

        return (
            f"STRUCTURED BRIEF (from Intake Agent):\n{brief_compact}\n\n"
            f"USE CASE MODEL:\n{uc_compact}\n\n"
            f"PROJECT PLAN (from Planning Agent):\n{plan_compact}\n\n"
            f"RISK REGISTER (from Risk Agent):\n{risk_compact}\n\n"
            "Run Step 8 + 8b + PM confidence score. "
            "Output StaffingPlanArtifact JSON only. No prose. No markdown."
        )
