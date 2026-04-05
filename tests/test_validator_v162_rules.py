"""v1.6.2 mechanical validator rules: urgency consistency, QA ratio risk, staffing assumptions."""

from agent.validator import SchemaValidator


def _five_phases_one_task():
    rows = [
        (1, 15),
        (2, 25),
        (3, 22),
        (4, 28),
        (5, 10),
    ]
    phases = []
    for n, pct in rows:
        tasks = []
        if n == 1:
            tasks.append(
                {
                    "id": "T1",
                    "name": "Spec APIs",
                    "phase": 1,
                    "effort_hours": 12.0,
                    "critical_path": True,
                    "slack_days": 0,
                }
            )
        phases.append(
            {
                "phase_number": n,
                "name": f"P{n}",
                "duration_weeks": 2,
                "percentage_of_total": pct,
                "milestones": ["M1"],
                "tasks": tasks,
            }
        )
    return phases


def _minimal_risks():
    return [
        {
            "id": "R1",
            "category": "Technical",
            "description": "Tech",
            "probability": "LOW",
            "impact": "MEDIUM",
            "score": "MEDIUM",
            "trigger": "t",
            "mitigation": "m",
        },
        {
            "id": "R2",
            "category": "Schedule",
            "description": "Sched",
            "probability": "LOW",
            "impact": "MEDIUM",
            "score": "MEDIUM",
            "trigger": "t",
            "mitigation": "m",
        },
        {
            "id": "R3",
            "category": "Resource",
            "description": "Res",
            "probability": "LOW",
            "impact": "MEDIUM",
            "score": "MEDIUM",
            "trigger": "t",
            "mitigation": "m",
        },
    ]


class TestBeforePlanningUrgencyConsistency:
    def test_errors_when_before_planning_but_plan_has_tasks(self):
        report = {
            "project_plan": {
                "total_duration_weeks": 12,
                "phases": _five_phases_one_task(),
            },
            "staffing_plan": [],
            "risk_register": _minimal_risks(),
            "assumption_log": [{"id": "A1", "what": "assumed"}],
            "pm_confidence_score": {"score": 70, "interpretation": "x"},
            "open_questions": [
                {
                    "priority": 1,
                    "question": "Unresolved scope?",
                    "urgency": "Before planning",
                    "impact_if_unanswered": "x",
                }
            ],
        }
        v = SchemaValidator()
        v._normalize_field_names(report)
        errors, _warnings = v._check_business_rules(report)
        assert any("Before planning" in e and "inconsistent" in e for e in errors)


class TestStaffingExpansionAssumptionCoverage:
    def test_warns_when_qa_added_without_assumption(self):
        report = {
            "project_understanding": {
                "primary_goal": "Two frontend and one backend developer deliver internal API.",
                "beneficiary": "Platform team",
                "trigger": "Need integration",
                "success_definition": ["API live"],
                "supporting_quotes": [],
            },
            "project_plan": {
                "total_duration_weeks": 10,
                "phases": _five_phases_one_task(),
            },
            "staffing_plan": [
                {
                    "role": "Frontend Developer",
                    "total_hours": 400.0,
                    "allocation_percent": 40.0,
                },
                {
                    "role": "Backend Developer",
                    "total_hours": 400.0,
                    "allocation_percent": 40.0,
                },
                {
                    "role": "QA Engineer",
                    "total_hours": 200.0,
                    "allocation_percent": 20.0,
                },
            ],
            "risk_register": _minimal_risks(),
            "assumption_log": [
                {
                    "id": "A1",
                    "what": "Developers commit full-time",
                    "why": "Needed",
                    "pmi_basis": "x",
                    "risk_if_wrong": "HIGH",
                    "consequence": "Slip",
                }
            ],
            "pm_confidence_score": {"score": 70, "interpretation": "x"},
            "open_questions": [],
        }
        v = SchemaValidator()
        v._normalize_field_names(report)
        _errors, warnings = v._check_business_rules(report)
        assert any(
            "QA" in w and "assumption_log" in w and "expanded role class" in w
            for w in warnings
        )


class TestQaRatioRiskSeverity:
    def test_errors_when_under_allocated_without_high_or_critical_risk(self):
        report = {
            "project_plan": {"total_duration_weeks": 10, "phases": _five_phases_one_task()},
            "staffing_plan": [
                {"role": "Developer", "total_hours": 400.0, "allocation_percent": 50},
                {"role": "QA Engineer", "total_hours": 40.0, "allocation_percent": 5},
            ],
            "risk_register": _minimal_risks(),
            "assumption_log": [{"id": "A1", "what": "x"}],
            "pm_confidence_score": {"score": 70, "interpretation": "x"},
            "open_questions": [],
        }
        v = SchemaValidator()
        v._normalize_field_names(report)
        errors, warnings = v._check_business_rules(report)
        assert any("25%" in e and "QA" in e for e in errors)
        assert not any("25%" in w and "QA" in w for w in warnings)

    def test_no_qa_ratio_warning_when_high_risk_present(self):
        risks = _minimal_risks()
        risks.append(
            {
                "id": "R4",
                "category": "Resource",
                "description": "QA hours set below 25% of developer hours due to schedule compression.",
                "probability": "HIGH",
                "impact": "HIGH",
                "score": "HIGH",
                "trigger": "Compression",
                "mitigation": "Borrow QA hours",
            }
        )
        report = {
            "project_plan": {"total_duration_weeks": 10, "phases": _five_phases_one_task()},
            "staffing_plan": [
                {"role": "Developer", "total_hours": 400.0, "allocation_percent": 50},
                {"role": "QA Engineer", "total_hours": 40.0, "allocation_percent": 5},
            ],
            "risk_register": risks,
            "assumption_log": [{"id": "A1", "what": "x"}],
            "pm_confidence_score": {"score": 70, "interpretation": "x"},
            "open_questions": [],
        }
        v = SchemaValidator()
        v._normalize_field_names(report)
        errors, warnings = v._check_business_rules(report)
        assert not any("25%" in e and "QA" in e for e in errors)
        assert not any("below 25%" in w for w in warnings)

    def test_errors_when_qa_ratio_risk_is_only_medium(self):
        risks = _minimal_risks()
        risks.append(
            {
                "id": "R4",
                "category": "Resource",
                "description": "QA hours sit below the 25% minimum vs developer effort.",
                "probability": "HIGH",
                "impact": "HIGH",
                "score": "MEDIUM",
                "trigger": "t",
                "mitigation": "m",
            }
        )
        report = {
            "project_plan": {"total_duration_weeks": 10, "phases": _five_phases_one_task()},
            "staffing_plan": [
                {"role": "Developer", "total_hours": 400.0, "allocation_percent": 50},
                {"role": "QA Engineer", "total_hours": 40.0, "allocation_percent": 5},
            ],
            "risk_register": risks,
            "assumption_log": [{"id": "A1", "what": "x"}],
            "pm_confidence_score": {"score": 70, "interpretation": "x"},
            "open_questions": [],
        }
        v = SchemaValidator()
        v._normalize_field_names(report)
        errors, _w = v._check_business_rules(report)
        assert any("25%" in e and "QA" in e for e in errors)


def _five_phases_no_tasks():
    rows = [(1, 15), (2, 25), (3, 22), (4, 28), (5, 10)]
    return [
        {
            "phase_number": n,
            "name": f"P{n}",
            "duration_weeks": 2,
            "percentage_of_total": pct,
            "milestones": ["M1"],
            "tasks": [],
        }
        for n, pct in rows
    ]


class TestSignOffOpenQuestionContradiction:
    def test_errors_before_planning_hr_signoff_when_assumption_claims_approval_complete(self):
        report = {
            "project_plan": {"total_duration_weeks": 14, "phases": _five_phases_no_tasks()},
            "staffing_plan": [],
            "risk_register": _minimal_risks(),
            "assumption_log": [
                {
                    "id": "A7",
                    "what": "Stakeholder approval for scope, timeline, and budget is assumed complete",
                    "why": "Input presents requirements as finalized",
                    "pmi_basis": "PMBOK 13.2",
                    "risk_if_wrong": "HIGH",
                    "consequence": "Re-planning",
                }
            ],
            "pm_confidence_score": {"score": 70, "interpretation": "x"},
            "open_questions": [
                {
                    "priority": 4,
                    "question": "Has the HR team formally signed off on scope, timeline, and budget in writing?",
                    "urgency": "Before planning",
                    "impact_if_unanswered": "Alignment risk",
                }
            ],
        }
        v = SchemaValidator()
        v._normalize_field_names(report)
        errors, _w = v._check_business_rules(report)
        assert any("Before build" in e and "contradiction" in e for e in errors)


class TestPhase5PercentageCeiling:
    def test_errors_when_phase5_percentage_exceeds_10(self):
        phases = _five_phases_one_task()
        for p in phases:
            if p["phase_number"] == 5:
                p["percentage_of_total"] = 10.7
        report = {
            "project_plan": {"total_duration_weeks": 14, "phases": phases},
            "staffing_plan": [],
            "risk_register": _minimal_risks(),
            "assumption_log": [{"id": "A1", "what": "x"}],
            "pm_confidence_score": {"score": 70, "interpretation": "x"},
            "open_questions": [],
        }
        v = SchemaValidator()
        v._normalize_field_names(report)
        errors, _w = v._check_business_rules(report)
        assert any("Phase 5" in e and "10%" in e for e in errors)


class TestPmStaffingAssumptionCoverage:
    def test_warns_when_product_manager_not_in_brief_without_assumption_row(self):
        report = {
            "project_understanding": {
                "primary_goal": "Two frontend and one backend developer deliver internal API.",
                "beneficiary": "Platform team",
                "trigger": "Need integration",
                "success_definition": ["API live"],
                "supporting_quotes": [],
            },
            "project_plan": {"total_duration_weeks": 10, "phases": _five_phases_one_task()},
            "staffing_plan": [
                {
                    "role": "Backend Developer",
                    "total_hours": 200.0,
                    "allocation_percent": 40.0,
                },
                {
                    "role": "Product Manager",
                    "total_hours": 70.0,
                    "allocation_percent": 15.0,
                },
            ],
            "risk_register": _minimal_risks(),
            "assumption_log": [
                {
                    "id": "A1",
                    "what": "Developers commit full-time",
                    "why": "Needed",
                    "pmi_basis": "x",
                    "risk_if_wrong": "HIGH",
                    "consequence": "Slip",
                }
            ],
            "pm_confidence_score": {"score": 70, "interpretation": "x"},
            "open_questions": [],
        }
        v = SchemaValidator()
        v._normalize_field_names(report)
        _errors, warnings = v._check_business_rules(report)
        assert any(
            "PM" in w and "expanded role class" in w and "assumption_log" in w for w in warnings
        )
