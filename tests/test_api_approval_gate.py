"""Unit tests for Project 2 approval gate rules (no HTTP)."""

from backend.api.services.approval_gate import evaluate_gate


def test_gate_not_fired_clean_report():
    report = {
        "pm_confidence_score": {"score": 75},
        "risk_register": [{"score": "HIGH"}],
        "project_viability": {"viability_status": "VIABLE"},
        "open_questions": [{"urgency": "Before build"}],
    }
    g = evaluate_gate(report)
    assert g.fired is False
    assert g.reasons == []


def test_gate_fires_low_confidence():
    report = {
        "pm_confidence_score": {"score": 55},
        "risk_register": [],
        "open_questions": [],
    }
    g = evaluate_gate(report)
    assert g.fired is True
    assert any("confidence" in r.lower() for r in g.reasons)


def test_gate_fires_critical_risk():
    report = {
        "pm_confidence_score": {"score": 80},
        "risk_register": [{"score": "CRITICAL"}],
        "open_questions": [],
    }
    g = evaluate_gate(report)
    assert g.fired is True
    assert any("CRITICAL" in r for r in g.reasons)


def test_gate_fires_not_viable():
    report = {
        "pm_confidence_score": {"score": 80},
        "risk_register": [],
        "project_viability": {"viability_status": "NOT_VIABLE"},
        "open_questions": [],
    }
    g = evaluate_gate(report)
    assert g.fired is True
    assert any("NOT_VIABLE" in r for r in g.reasons)


def test_gate_fires_before_planning_question():
    report = {
        "pm_confidence_score": {"score": 80},
        "risk_register": [],
        "open_questions": [{"urgency": "Before planning"}],
    }
    g = evaluate_gate(report)
    assert g.fired is True


def test_gate_fires_both_low_confidence_and_critical_risk():
    """Both reasons must appear when confidence < 60 AND a CRITICAL risk exist simultaneously."""
    report = {
        "pm_confidence_score": {"score": 55},
        "risk_register": [{"score": "CRITICAL", "title": "Unresolved integration"}],
        "open_questions": [],
    }
    g = evaluate_gate(report)
    assert g.fired is True
    assert any("confidence" in r.lower() for r in g.reasons)
    assert any("CRITICAL" in r for r in g.reasons)
    assert len(g.reasons) == 2


def test_gate_fires_at_score_59():
    """Boundary: 59 is strictly below 60, gate must fire."""
    report = {"pm_confidence_score": {"score": 59}, "risk_register": [], "open_questions": []}
    g = evaluate_gate(report)
    assert g.fired is True


def test_gate_does_not_fire_at_score_60():
    """Boundary: 60 is not below 60, gate must not fire on score alone."""
    report = {"pm_confidence_score": {"score": 60}, "risk_register": [], "open_questions": []}
    g = evaluate_gate(report)
    assert g.fired is False


def test_gate_does_not_fire_at_score_61():
    """Boundary: 61 is above threshold, gate must not fire on score alone."""
    report = {"pm_confidence_score": {"score": 61}, "risk_register": [], "open_questions": []}
    g = evaluate_gate(report)
    assert g.fired is False


def test_gate_does_not_fire_before_planning_when_plan_already_decomposed():
    """Mis-tagged 'Before planning' must not block if WBS is present (v16.2 rubric alignment)."""
    phases = [{"name": f"P{i}", "tasks": [{"id": f"T{i}", "title": "x"}]} for i in range(5)]
    report = {
        "pm_confidence_score": {"score": 80},
        "risk_register": [],
        "project_plan": {"phases": phases},
        "open_questions": [{"urgency": "Before planning", "question": "HR sign-off in writing?"}],
    }
    g = evaluate_gate(report)
    assert g.fired is False
    assert not any("Before planning" in r for r in g.reasons)
