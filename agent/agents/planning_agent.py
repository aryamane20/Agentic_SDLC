import json
from pathlib import Path

from agent.base_agent import BaseAgent, MODEL_HAIKU

_PROMPT = Path(__file__).parent.parent.parent / "prompts/agents/planning_v1.1.txt"


class PlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="planning",
            prompt_path=_PROMPT,
            model=MODEL_HAIKU,
            max_tokens=8192,
        )

    def _is_valid_artifact(self, parsed: dict) -> bool:
        return isinstance(parsed, dict) and "project_plan" in parsed

    def _build_user_message(self, context: dict) -> str:
        brief = context.get("structured_brief", {})
        use_case = context.get("use_case_model", {})

        # Compact JSON — drop raw_brief to avoid duplicating large text
        brief_compact = json.dumps(brief, separators=(",", ":"))
        uc_compact = json.dumps(use_case, separators=(",", ":"))

        return (
            f"STRUCTURED BRIEF (from Intake Agent):\n{brief_compact}\n\n"
            f"USE CASE MODEL:\n{uc_compact}\n\n"
            "Run Steps 5–6. Output ProjectPlanArtifact JSON only. No prose. No markdown."
        )
