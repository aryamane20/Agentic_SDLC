import json
from pathlib import Path

from agent.base_agent import BaseAgent, MODEL_HAIKU

_PROMPT = Path(__file__).parent.parent.parent / "prompts/agents/synthesis_v1.0.txt"


class SynthesisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="synthesis",
            prompt_path=_PROMPT,
            model=MODEL_HAIKU,
            max_tokens=8192,
        )

    def _is_valid_artifact(self, parsed: dict) -> bool:
        return isinstance(parsed, dict) and "pm_confidence_score" in parsed

    def _build_user_message(self, context: dict) -> str:
        use_case = context.get("use_case_model", {})
        brief = context.get("structured_brief", {})
        plan = context.get("project_plan", {})
        risk = context.get("risk_register_artifact", {})
        staffing = context.get("staffing_plan_artifact", {})

        # Compact JSON for all 5 artifacts
        artifacts = {
            "use_case_model": use_case,
            "structured_brief": brief,
            "project_plan": plan,
            "risk_register_artifact": risk,
            "staffing_plan_artifact": staffing,
        }
        artifacts_compact = json.dumps(artifacts, separators=(",", ":"))

        return (
            f"ALL PIPELINE ARTIFACTS:\n{artifacts_compact}\n\n"
            "Apply all 5 consistency rules, assemble the final PMReport, and output "
            "SynthesisResult JSON only. No prose. No markdown."
        )
