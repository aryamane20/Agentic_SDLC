"""
Approval gate triggers — pure functions, no I/O.
See docs/ARCHITECTURE.md § Project 2: confidence, CRITICAL risks, NOT_VIABLE, open questions.
"""

from backend.api.models.gate import GateState


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
            fired = True
            reasons.append("risk_register contains CRITICAL risk — PM decision required")
            break

    pv = report.get("project_viability") or {}
    if pv.get("viability_status") == "NOT_VIABLE":
        fired = True
        reasons.append("project_viability is NOT_VIABLE — impossible constraints as stated")

    for oq in report.get("open_questions") or []:
        if oq.get("urgency") == "Before planning":
            fired = True
            reasons.append(
                "open_questions include urgency Before planning — resolve before trusting plan"
            )
            break

    return GateState(fired=fired, reasons=reasons, decision=None)
