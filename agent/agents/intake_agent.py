import json
from pathlib import Path

from agent.base_agent import BaseAgent, MODEL_HAIKU

_PROMPT = Path(__file__).parent.parent.parent / "prompts/agents/intake_v1.1.txt"


class IntakeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="intake",
            prompt_path=_PROMPT,
            model=MODEL_HAIKU,
            max_tokens=4000,
        )

    def _is_valid_artifact(self, parsed: dict) -> bool:
        return isinstance(parsed, dict) and (
            "project_understanding" in parsed or "report_metadata" in parsed
        )

    def _build_user_message(self, context: dict) -> str:
        brief = context.get("raw_brief", "")
        use_case = context.get("use_case_model", {})
        uc_summary = json.dumps(use_case, separators=(",", ":"))
        return (
            f"USE CASE MODEL (from Use Case Agent):\n{uc_summary}\n\n"
            f"PROJECT BRIEF:\n---\n{brief}\n---\n\n"
            "Run Steps 1–4. Output StructuredBrief JSON only. No prose. No markdown."
        )
