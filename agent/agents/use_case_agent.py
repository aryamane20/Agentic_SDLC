import json
from pathlib import Path

from agent.base_agent import BaseAgent, MODEL_HAIKU

_PROMPT = Path(__file__).parent.parent.parent / "prompts/agents/use_case_v1.0.txt"


class UseCaseAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="use_case",
            prompt_path=_PROMPT,
            model=MODEL_HAIKU,
            max_tokens=2000,
        )

    def _is_valid_artifact(self, parsed: dict) -> bool:
        return isinstance(parsed, dict) and "actors" in parsed

    def _build_user_message(self, context: dict) -> str:
        brief = context.get("raw_brief", "")
        return (
            f"PROJECT BRIEF:\n---\n{brief}\n---\n\n"
            "Extract the use case model. Output JSON only. No prose. No markdown."
        )
