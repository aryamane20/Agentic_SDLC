"""Hard-cap must survive validator normalize (breakdown.starting_score used to undo it)."""

from agent.main import PMAgent
from agent.validator import SchemaValidator


def _report_pm_cap_fixture():
    return {
        "assumption_log": [{"id": f"A{i}", "what": "w"} for i in range(5)],
        "risk_register": [{"id": "r1"}, {"id": "r2"}, {"id": "r3"}],
        "pm_confidence_score": {
            "score": 78,
            "breakdown": {
                "starting_score": 78,
                "interpretation": "Calculated PM confidence is 78 based on inputs.",
            },
        },
        "report_metadata": {"generated_at": "2026-01-01T00:00:00Z"},
        "project_plan": {
            "phases": [
                {
                    "phase_number": n,
                    "name": f"P{n}",
                    "duration_weeks": 2,
                    "percentage_of_total": pct,
                    "milestones": ["M"],
                    "tasks": [],
                }
                for n, pct in [(1, 15), (2, 25), (3, 22), (4, 28), (5, 10)]
            ]
        },
        "staffing_plan": [],
        "open_questions": [{"question": "q", "urgency": "Low"}],
    }


def test_cap_drops_breakdown_normalize_cannot_restore_higher_score():
    agent = PMAgent(prompt_version="v1.6.2")
    v = SchemaValidator()
    report = _report_pm_cap_fixture()

    agent._enforce_hard_caps(report)
    assert report["pm_confidence_score"]["score"] == 60
    assert "breakdown" not in report["pm_confidence_score"]
    # Single authoritative numeric is `score` (60); prose may cite pre-cap model value for audit.

    v._normalize_field_names(report)
    assert float(report["pm_confidence_score"]["score"]) == 60


def test_second_enforce_after_normalize_reapplies_cap_when_breakdown_present():
    """If normalize ever reintroduces breakdown from bad merge, second enforce fixes score."""
    agent = PMAgent(prompt_version="v1.6.2")
    v = SchemaValidator()
    report = _report_pm_cap_fixture()
    # Simulate stale merge: capped score but breakdown still present (pre-fix agent).
    report["pm_confidence_score"] = {
        "score": 60,
        "breakdown": {"starting_score": 78},
        "deductions": [],
        "interpretation": "Stale",
    }

    v._normalize_field_names(report)
    assert float(report["pm_confidence_score"]["score"]) == 78

    agent._enforce_hard_caps(report)
    assert float(report["pm_confidence_score"]["score"]) == 60
    assert "breakdown" not in report["pm_confidence_score"]
