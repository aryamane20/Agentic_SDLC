"""
PM Confidence Score — pure Python computation.

Implements the exact 4-step formula from prompts/agents/synthesis_v1.0.txt Rule 4.
Called inside synthesis_node after the LLM returns to replace the LLM's numeric score
with an authoritative, deterministic value.

The LLM-generated deductions text and interpretation prose are kept; only
pm_confidence_score["score"] is overwritten and the interpretation number patched.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ConfidenceResult:
    score: float
    deductions: List[Dict]
    interpretation: str
    raw_score_before_caps: float


def compute_confidence(
    *,
    assumption_count: int,
    high_risk_count: int,
    critical_risk_count: int,
    unknown_constraints: int,
    input_quality: Optional[str],       # "HIGH" | "MEDIUM" | "LOW" | None
    sdlc_approach: Optional[str],       # "Waterfall" | "Hybrid" | "Adaptive" | None
    project_type: Optional[str],        # "TYPE_A" … "TYPE_F" | None
    total_duration_weeks: float,
) -> ConfidenceResult:
    """
    Compute pm_confidence_score from raw counts.

    Step 2 deductions (non-zero only):
      -5 × unknown_constraints
      -5 × assumption_count
      -10 if input_quality == "LOW" else -5 if "MEDIUM" else 0
      -10 if critical_risk_count >= 1  (flat, not per-risk)
      -5 × high_risk_count
      -5 if sdlc in ("Adaptive", "Hybrid")
      -10 if total_duration_weeks < 6 AND project_type in ("TYPE_A", "TYPE_D")

    Step 3 hard caps (applied after deductions):
      assumption >= 8  → cap 40
      assumption >= 5  → cap 60
      critical >= 1 AND assumption >= 3 → cap 50
      input_quality == "LOW" → cap 45

    Step 4: floor at 10.
    """
    raw = 100.0
    deductions: List[Dict] = []

    # --- Step 2: deductions ---
    if unknown_constraints > 0:
        amt = 5.0 * unknown_constraints
        raw -= amt
        deductions.append({"amount": amt, "reason": f"{unknown_constraints} unknown hard constraint(s) × 5"})

    if assumption_count > 0:
        amt = 5.0 * assumption_count
        raw -= amt
        deductions.append({"amount": amt, "reason": f"{assumption_count} assumption(s) × 5"})

    if input_quality == "LOW":
        raw -= 10.0
        deductions.append({"amount": 10.0, "reason": "LOW input quality"})
    elif input_quality == "MEDIUM":
        raw -= 5.0
        deductions.append({"amount": 5.0, "reason": "MEDIUM input quality"})

    if critical_risk_count >= 1:
        raw -= 10.0
        deductions.append({"amount": 10.0, "reason": f"{critical_risk_count} CRITICAL risk(s) (flat -10)"})

    if high_risk_count > 0:
        amt = 5.0 * high_risk_count
        raw -= amt
        deductions.append({"amount": amt, "reason": f"{high_risk_count} HIGH risk(s) × 5"})

    if sdlc_approach in ("Adaptive", "Hybrid"):
        raw -= 5.0
        deductions.append({"amount": 5.0, "reason": f"{sdlc_approach} SDLC"})

    if total_duration_weeks < 6 and project_type in ("TYPE_A", "TYPE_D"):
        raw -= 10.0
        deductions.append({"amount": 10.0, "reason": "Short timeline (<6w) for TYPE_A/D project"})

    raw_before_caps = raw

    # --- Step 3: hard caps ---
    if assumption_count >= 8:
        raw = min(raw, 40.0)
    elif assumption_count >= 5:
        raw = min(raw, 60.0)
    if critical_risk_count >= 1 and assumption_count >= 3:
        raw = min(raw, 50.0)
    if input_quality == "LOW":
        raw = min(raw, 45.0)

    # --- Step 4: floor ---
    final = max(raw, 10.0)

    interpretation = _build_interpretation(
        final, assumption_count, critical_risk_count, high_risk_count,
        sdlc_approach, input_quality,
    )

    return ConfidenceResult(
        score=final,
        deductions=deductions,
        interpretation=interpretation,
        raw_score_before_caps=raw_before_caps,
    )


def extract_confidence_inputs(
    use_case_artifact: dict,
    intake_artifact: dict,
    risk_artifact: dict,
    planning_artifact: dict,
) -> dict:
    """
    Extract the raw counts needed by compute_confidence() from pipeline artifacts.

    Returns a kwargs dict ready for compute_confidence(**extract_confidence_inputs(...)).
    """
    risks = risk_artifact.get("risk_register", [])
    pp    = planning_artifact.get("project_plan", {})
    meta  = intake_artifact.get("report_metadata", {})

    hard = intake_artifact.get("constraints", {}).get("hard", {})
    # Only deadline, budget, and team_size being unknown block planning.
    # technology_stack, team_composition, and compliance null = acceptable early-stage unknowns.
    _PLANNING_CRITICAL = {"deadline", "budget", "team_size"}
    if isinstance(hard, dict):
        unknown_constraints = sum(
            1 for k, v in hard.items() if k in _PLANNING_CRITICAL and v is None
        )
    else:
        unknown_constraints = 0

    return {
        "assumption_count":    len(intake_artifact.get("assumption_log", [])),
        "high_risk_count":     sum(1 for r in risks if r.get("score") == "HIGH"),
        "critical_risk_count": sum(1 for r in risks if r.get("score") == "CRITICAL"),
        "unknown_constraints": unknown_constraints,
        "input_quality":       use_case_artifact.get("input_quality_signal"),
        "sdlc_approach":       meta.get("sdlc_approach"),
        "project_type":        meta.get("project_type"),
        "total_duration_weeks": float(pp.get("total_duration_weeks") or 99),
    }


def patch_synthesis_artifact(synthesis_artifact: dict, result: ConfidenceResult) -> dict:
    """
    Replace the LLM-computed numeric score in a synthesis artifact with the
    Python-computed authoritative value. Keeps the LLM's deductions text but
    patches the interpretation to reference the correct number.

    Mutates and returns the artifact dict.
    """
    cs = synthesis_artifact.get("pm_confidence_score")
    if isinstance(cs, dict):
        cs["score"] = result.score
        # Patch interpretation so it cites the correct number
        interp = cs.get("interpretation", "")
        cs["interpretation"] = _patch_interpretation(interp, result.score, result.interpretation)
    else:
        synthesis_artifact["pm_confidence_score"] = {
            "score": result.score,
            "deductions": result.deductions,
            "interpretation": result.interpretation,
        }
    return synthesis_artifact


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_interpretation(
    score: float,
    assumption_count: int,
    critical_risk_count: int,
    high_risk_count: int,
    sdlc_approach: Optional[str],
    input_quality: Optional[str],
) -> str:
    reasons = []
    if critical_risk_count >= 1:
        reasons.append(f"{critical_risk_count} CRITICAL risk(s)")
    if assumption_count >= 5:
        reasons.append(f"{assumption_count} assumptions (cap applied)")
    elif assumption_count > 0:
        reasons.append(f"{assumption_count} assumption(s)")
    if high_risk_count > 0:
        reasons.append(f"{high_risk_count} HIGH risk(s)")
    if sdlc_approach in ("Adaptive", "Hybrid"):
        reasons.append(f"{sdlc_approach} SDLC")
    if input_quality in ("LOW", "MEDIUM"):
        reasons.append(f"{input_quality} input quality")
    reason_str = ", ".join(reasons) if reasons else "standard deductions applied"
    return f"PM confidence score is {score} because {reason_str}."


def _patch_interpretation(original: str, correct_score: float, fallback: str) -> str:
    """Replace a stale score number in the LLM's interpretation string."""
    import re
    # Replace patterns like "score is 62", "score is 62.0", "is 62 because"
    patched = re.sub(
        r"(score\s+is\s+)\d+(?:\.\d+)?",
        lambda m: m.group(1) + str(correct_score),
        original,
        flags=re.IGNORECASE,
    )
    # If nothing matched (LLM used a different phrase), fall back to generated
    return patched if patched != original else fallback
