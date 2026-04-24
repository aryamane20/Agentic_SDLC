"""Staffing over-allocation warnings vs project viability (NOT_VIABLE)."""

from agent.validator import SchemaValidator


def _five_valid_phases():
    return [
        {
            "phase_number": n,
            "name": f"Phase {n}",
            "duration_weeks": 2,
            "percentage_of_total": pct,
            "milestones": ["M1"],
            "tasks": [],
        }
        for n, pct in [(1, 15), (2, 15), (3, 20), (4, 40), (5, 10)]
    ]


def _minimal_report_for_business_rules():
    """Enough structure for _check_business_rules without full Pydantic path."""
    return {
        "project_plan": {"phases": _five_valid_phases()},
        "staffing_plan": [
            {
                "role": "Solo Engineer",
                "phase_involvement": [1, 2, 3, 4, 5],
                "total_hours": 400,
                "allocation_percent": 100,
                "skills_required": [],
                "critical_path": True,
            }
        ],
        "risk_register": [{"id": "R1"}, {"id": "R2"}, {"id": "R3"}],
        "assumption_log": [{"id": "A1", "what": "x"}],
        "pm_confidence_score": {"score": 45, "deductions": [], "interpretation": "Low"},
        "project_viability": {
            "viability_status": "NOT_VIABLE",
            "gap_type": "BOTH",
            "scoping_options": [
                {"summary": "Reduce scope", "notes": "A"},
                {"summary": "Add budget", "notes": "B"},
            ],
        },
    }


def _overallocation_warnings(warnings):
    return [w for w in warnings if "exceeds 80%" in w]


class TestOverallocationNotViable:
    def test_no_overallocation_warning_when_not_viable(self):
        v = SchemaValidator()
        report = _minimal_report_for_business_rules()
        v._normalize_field_names(report)
        _errors, warnings = v._check_business_rules(report)
        assert _overallocation_warnings(warnings) == []

    def test_overallocation_warning_when_viable(self):
        v = SchemaValidator()
        report = _minimal_report_for_business_rules()
        report["project_viability"] = {
            "viability_status": "VIABLE",
            "gap_type": None,
            "scoping_options": [],
        }
        v._normalize_field_names(report)
        _errors, warnings = v._check_business_rules(report)
        assert len(_overallocation_warnings(warnings)) == 1

    def test_overallocation_warning_when_no_viability_section(self):
        v = SchemaValidator()
        report = _minimal_report_for_business_rules()
        del report["project_viability"]
        v._normalize_field_names(report)
        _errors, warnings = v._check_business_rules(report)
        assert len(_overallocation_warnings(warnings)) == 1
