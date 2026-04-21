"""
Approval gate triggers — pure functions, no I/O.
See docs/ARCHITECTURE.md § Project 2: confidence, CRITICAL risks, NOT_VIABLE, open questions.
"""

from backend.api.models.gate import GateState


def _plan_has_decomposed_tasks(report: dict) -> bool:
    """
    True when the report already contains a populated WBS (5 phases typical, ≥1 task).
    If so, an open_question labeled "Before planning" is a self-contradiction with the
    v1.6.2 rubric (decomposition already happened) — do not block the gate on that label.
    """
    phases = (report.get("project_plan") or {}).get("phases") or []
    if len(phases) < 5:
        return False
    task_count = sum(len(p.get("tasks") or []) for p in phases)
    return task_count >= 1


def _confidence_score(report: dict) -> float | None:
    cs = report.get("pm_confidence_score")
    if isinstance(cs, dict):
        s = cs.get("score")
    else:
        s = cs
    if s is None:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def evaluate_gate(report: dict) -> GateState:
    fired = False
    reasons: list[str] = []

    score = _confidence_score(report)
    if score is not None and score < 60:
        fired = True
        reasons.append("confidence_score < 60 — plan needs review")

    for r in report.get("risk_register") or []:
        if r.get("score") == "CRITICAL":
            reasons.append("risk_register contains CRITICAL risk — PM decision required")
    fired = bool(reasons)

    pv = report.get("project_viability") or {}
    if pv.get("viability_status") == "NOT_VIABLE":
        fired = True
        reasons.append("project_viability is NOT_VIABLE — impossible constraints as stated")

    # "Before planning" is blocking only when the model did not already output a decomposed plan.
    if _plan_has_decomposed_tasks(report):
        pass  # mis-tagged urgency; validator / prompt v1.6.2 — trust WBS, resolve questions as pre-build
    else:
        for oq in report.get("open_questions") or []:
            if oq.get("urgency") == "Before planning":
                fired = True
                reasons.append(
                    "open_questions include urgency Before planning — resolve before trusting plan"
                )
                break

    return GateState(fired=fired, reasons=reasons, decision=None)
