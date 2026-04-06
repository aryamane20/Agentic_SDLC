"""Viability checker: critical path duration uses working-day weeks (5 d/wk)."""

from agent.viability_checker import ViabilityChecker


def test_total_duration_days_divides_by_five_not_seven():
    vc = ViabilityChecker()
    report = {
        "project_plan": {
            "critical_path_summary": {"total_duration_days": 56.0},
        }
    }
    weeks = vc._extract_critical_path_duration(report)
    assert weeks == 11.2
