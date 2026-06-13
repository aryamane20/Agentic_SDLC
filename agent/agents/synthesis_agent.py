import json
from pathlib import Path

from agent.base_agent import BaseAgent, MODEL_HAIKU

_PROMPT = Path(__file__).parent.parent.parent / "prompts/agents/synthesis_v1.1.txt"


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

    def _post_process_artifact(self, artifact: dict) -> dict:
        """Strip PASS-condition log entries from consistency_issues.

        The model sometimes logs passing checks as consistency_issues. Remove:
        - Rule 1 (actor_role_coverage): only auto_corrected=True entries are real failures
        - Rule 3 (use_case_task_coverage): only entries where detail says 'has no tasks'
        - Any rule: if the detail explicitly contains 'PASS'
        """
        issues = artifact.get("consistency_issues", [])
        filtered = []
        for i in issues:
            rule = i.get("rule", "")
            detail = str(i.get("detail", ""))
            auto_corrected = i.get("auto_corrected", False)

            if rule == "actor_role_coverage" and not auto_corrected:
                continue  # Rule 1 PASS log — real failures always auto_corrected=True
            if rule == "use_case_task_coverage" and "has no tasks" not in detail:
                continue  # Rule 3 PASS log — real failures mention missing tasks
            if "PASS" in detail:
                continue  # Generic PASS log in any rule

            filtered.append(i)
        artifact["consistency_issues"] = filtered
        return artifact

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
