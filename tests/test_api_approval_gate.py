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
