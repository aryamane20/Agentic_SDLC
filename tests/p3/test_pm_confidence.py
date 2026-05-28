"""
Tests for agent/pm_confidence.py — pure arithmetic, no mocks, no API calls.

All expected values computed by hand from the formula in synthesis_v1.0.txt Rule 4.
"""

import json
from pathlib import Path

import pytest

from agent.pm_confidence import (
    ConfidenceResult,
    compute_confidence,
    extract_confidence_inputs,
    patch_synthesis_artifact,
)

FIXTURE_DIR = Path(__file__).parent.parent.parent / "inputs" / "test-cases-p3" / "fixtures"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _compute(**overrides) -> ConfidenceResult:
    """Call compute_confidence with safe defaults, overriding named fields."""
    defaults = dict(
        assumption_count=0,
        high_risk_count=0,
        critical_risk_count=0,
        unknown_constraints=0,
        input_quality="HIGH",
        sdlc_approach="Waterfall",
        project_type="TYPE_B",
        total_duration_weeks=12.0,
    )
    defaults.update(overrides)
    return compute_confidence(**defaults)


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------

def test_perfect_input_scores_100():
    r = _compute()
    assert r.score == 100.0
    assert r.deductions == []


# ---------------------------------------------------------------------------
# Step 2: individual deductions
# ---------------------------------------------------------------------------

def test_unknown_constraints_deduction():
    r = _compute(unknown_constraints=2)
    assert r.score == 90.0
    assert any(d["amount"] == 10.0 for d in r.deductions)


def test_assumption_deduction_five_points_each():
    r = _compute(assumption_count=3)
    assert r.score == 85.0


def test_low_quality_deducts_10_then_caps_at_45():
    r = _compute(input_quality="LOW")
    # 100 - 10 = 90 raw, then LOW cap fires → 45
    assert r.raw_score_before_caps == 90.0
    assert r.score == 45.0


def test_medium_quality_deducts_5():
    r = _compute(input_quality="MEDIUM")
    assert r.score == 95.0


def test_high_quality_no_deduction():
    r = _compute(input_quality="HIGH")
    assert r.score == 100.0


def test_critical_risk_flat_10_not_per_risk():
    # 3 CRITICAL risks → still only -10 (flat)
    r1 = _compute(critical_risk_count=1)
    r3 = _compute(critical_risk_count=3)
    assert r1.score == r3.score == 90.0


def test_high_risk_five_points_each():
    r = _compute(high_risk_count=4)
    assert r.score == 80.0


def test_hybrid_sdlc_deducts_5():
    r = _compute(sdlc_approach="Hybrid")
    assert r.score == 95.0


def test_adaptive_sdlc_deducts_5():
    r = _compute(sdlc_approach="Adaptive")
    assert r.score == 95.0


def test_waterfall_sdlc_no_deduction():
    r = _compute(sdlc_approach="Waterfall")
    assert r.score == 100.0


def test_short_timeline_type_a_deducts_10():
    r = _compute(total_duration_weeks=4, project_type="TYPE_A")
    assert r.score == 90.0


def test_short_timeline_type_d_deducts_10():
    r = _compute(total_duration_weeks=5, project_type="TYPE_D")
    assert r.score == 90.0


def test_short_timeline_other_types_no_deduction():
    r = _compute(total_duration_weeks=4, project_type="TYPE_B")
    assert r.score == 100.0


def test_normal_timeline_no_deduction():
    r = _compute(total_duration_weeks=8, project_type="TYPE_A")
    assert r.score == 100.0


# ---------------------------------------------------------------------------
# Step 3: hard caps
# ---------------------------------------------------------------------------

def test_cap_40_for_8_or_more_assumptions():
    # Without cap: 100 - 8*5 = 60 → cap fires → 40
    r = _compute(assumption_count=8)
    assert r.score == 40.0


def test_cap_60_for_5_to_7_assumptions():
    # Without cap: 100 - 5*5 = 75 → cap fires → 60
    r = _compute(assumption_count=5)
    assert r.score == 60.0


def test_cap_50_for_critical_plus_3_assumptions():
    # Without cap: 100 - 3*5 - 10 = 75 → cap fires → 50
    r = _compute(critical_risk_count=1, assumption_count=3)
    assert r.score == 50.0


def test_cap_45_for_low_quality():
    r = _compute(input_quality="LOW")
    assert r.score == 45.0  # 100 - 10 = 90 raw → LOW cap → 45


def test_strictest_cap_wins():
    # assumption_count=8 → cap 40; critical+3 → cap 50; LOW → cap 45
    # Strictest: 40
    r = _compute(assumption_count=8, critical_risk_count=1, input_quality="LOW")
    assert r.score == 40.0


def test_cap_8_assumptions_takes_priority_over_5():
    r = _compute(assumption_count=8)
    assert r.score == 40.0


# ---------------------------------------------------------------------------
# Step 4: floor at 10
# ---------------------------------------------------------------------------

def test_floor_at_10():
    # Pile on everything: 10 assumptions, 5 HIGH, 2 CRITICAL, Hybrid, LOW, 3 unknown
    r = _compute(
        assumption_count=10,
        high_risk_count=10,
        critical_risk_count=2,
        unknown_constraints=3,
        input_quality="LOW",
        sdlc_approach="Hybrid",
    )
    assert r.score == 10.0


# ---------------------------------------------------------------------------
# Fixture-based integration tests (known correct answers)
# ---------------------------------------------------------------------------

def _load_fixtures(tc: str):
    uc     = json.loads((FIXTURE_DIR / "use_case"  / f"{tc}.json").read_text())
    intake = json.loads((FIXTURE_DIR / "intake"    / f"{tc}.json").read_text())
    risk   = json.loads((FIXTURE_DIR / "risk"      / f"{tc}.json").read_text())
    plan   = json.loads((FIXTURE_DIR / "planning"  / f"{tc}.json").read_text())
    return uc, intake, risk, plan


def test_tc01_perfect_score():
    # 5 assumptions, 2 CRITICAL, 4 HIGH, Hybrid → raw 40; cap(5 assump)→60 no effect, CRIT+3→50 no effect
    uc, intake, risk, plan = _load_fixtures("tc-01-perfect")
    inputs = extract_confidence_inputs(uc, intake, risk, plan)
    result = compute_confidence(**inputs)
    assert result.score == 40.0
    assert result.raw_score_before_caps == 40.0


def test_tc02_good_score():
    # 3 assumptions, 3 CRITICAL, 5 HIGH, 1 unknown, Hybrid → raw 40; CRIT+3 assump cap→50 no effect
    uc, intake, risk, plan = _load_fixtures("tc-02-good")
    inputs = extract_confidence_inputs(uc, intake, risk, plan)
    result = compute_confidence(**inputs)
    assert result.score == 40.0


def test_tc03_medium_score():
    # 5 assumptions, 2 CRITICAL, 5 HIGH, 1 unknown (budget only), Hybrid → raw 30
    # technology_stack and compliance null no longer count as planning-critical unknowns
    uc, intake, risk, plan = _load_fixtures("tc-03-medium")
    inputs = extract_confidence_inputs(uc, intake, risk, plan)
    result = compute_confidence(**inputs)
    assert result.score == 30.0


# ---------------------------------------------------------------------------
# Deductions sum check
# ---------------------------------------------------------------------------

def test_deductions_sum_equals_100_minus_raw_before_caps():
    r = _compute(assumption_count=4, high_risk_count=3, critical_risk_count=1, sdlc_approach="Hybrid")
    total_deducted = sum(d["amount"] for d in r.deductions)
    assert total_deducted == pytest.approx(100.0 - r.raw_score_before_caps)


# ---------------------------------------------------------------------------
# patch_synthesis_artifact
# ---------------------------------------------------------------------------

def test_patch_replaces_score_in_artifact():
    artifact = {
        "pm_confidence_score": {
            "score": 62.0,
            "deductions": [],
            "interpretation": "PM confidence score is 62.0 because many risks.",
        }
    }
    result = ConfidenceResult(score=40.0, deductions=[], interpretation="...", raw_score_before_caps=40.0)
    patched = patch_synthesis_artifact(artifact, result)
    assert patched["pm_confidence_score"]["score"] == 40.0


def test_patch_updates_interpretation_number():
    artifact = {
        "pm_confidence_score": {
            "score": 62.0,
            "interpretation": "PM confidence score is 62.0 because high risk.",
        }
    }
    result = ConfidenceResult(score=40.0, deductions=[], interpretation="...", raw_score_before_caps=40.0)
    patched = patch_synthesis_artifact(artifact, result)
    assert "40.0" in patched["pm_confidence_score"]["interpretation"]
    assert "62" not in patched["pm_confidence_score"]["interpretation"]


def test_patch_handles_missing_pm_confidence_score():
    artifact = {}
    result = ConfidenceResult(score=55.0, deductions=[], interpretation="score is 55", raw_score_before_caps=55.0)
    patched = patch_synthesis_artifact(artifact, result)
    assert patched["pm_confidence_score"]["score"] == 55.0
