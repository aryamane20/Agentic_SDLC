"""Shared helpers and fixtures for P3 tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
P3_FIXTURES = REPO_ROOT / "inputs" / "test-cases-p3" / "fixtures"
P3_INPUTS   = REPO_ROOT / "inputs" / "test-cases-p3"


def load_fixture(agent: str, name: str) -> dict:
    """Load a frozen JSON artifact from inputs/test-cases-p3/fixtures/{agent}/{name}.json"""
    path = P3_FIXTURES / agent / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_brief(name: str) -> str:
    """Load a brief .txt from inputs/test-cases-p3/{name}.txt"""
    path = P3_INPUTS / f"{name}.txt"
    if not path.is_file():
        # Fall back to P1 test cases
        path = REPO_ROOT / "inputs" / "test-cases-p1" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def make_mock_response(json_payload: dict) -> Mock:
    """Build a mock Anthropic API response containing json_payload as text."""
    import json as _json
    mock_resp = Mock()
    mock_resp.content = [Mock(text=_json.dumps(json_payload))]
    mock_resp.usage = Mock(
        input_tokens=500,
        output_tokens=300,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    return mock_resp


# ---------------------------------------------------------------------------
# Minimal stub artifacts — used by unit tests to feed downstream agents
# ---------------------------------------------------------------------------

@pytest.fixture
def stub_use_case_model():
    return {
        "system_boundary": "Internal Dashboard",
        "actors": [
            {"id": "A1", "name": "Data Analyst", "type": "primary"},
            {"id": "A2", "name": "Notification Service", "type": "external"},
        ],
        "use_cases": [
            {"id": "UC1", "name": "View Pipeline Status", "actors": ["A1"], "complexity": "simple"},
            {"id": "UC2", "name": "Generate Report", "actors": ["A1"], "complexity": "medium"},
        ],
        "relationships": [],
        "input_quality_signal": "HIGH",
        "anti_patterns_detected": [],
    }


@pytest.fixture
def stub_structured_brief():
    return {
        "project_understanding": {
            "primary_goal": "Build internal data pipeline dashboard",
            "beneficiary": "Data Analytics team",
            "trigger": "Manual monitoring is error-prone",
            "success_definition": ["Real-time pipeline status visible", "Alert on failures"],
            "supporting_quotes": ["monitors data pipelines manually"],
        },
        "assumption_log": [
            {
                "id": "A1", "what": "SSO authentication assumed",
                "why": "Standard for internal tools", "pmi_basis": "PMBOK 6th Ed, Section 8.1",
                "risk_if_wrong": "HIGH", "consequence": "Security re-architecture required",
                "source": "nfr", "tradeoff": "Gains: planning proceeds. Risks: auth re-work.",
            }
        ],
        "report_metadata": {
            "project_type": "TYPE_C",
            "input_quality": "HIGH",
            "classification_confidence": "HIGH",
            "sdlc_approach": "Hybrid",
            "sdlc_rationale": "Fixed deadline with evolving data requirements.",
        },
        "constraints": {
            "hard": {"deadline": "3 months", "budget": "$50,000", "team_size": 3,
                     "team_composition": "2 backend, 1 frontend", "technology_stack": None, "compliance": None},
            "soft": {"preferred_timeline": None, "preferred_tools": None, "nice_to_have": []},
            "nfr": {"security": None, "data_retention": None, "performance": None, "availability": None},
        },
        "open_questions_pre_planning": [],
    }


@pytest.fixture
def stub_project_plan():
    return {
        "project_plan": {
            "total_duration_weeks": 12.0,
            "buffer_applied_percent": 15.0,
            "critical_path_summary": {
                "sequence": ["T1", "T3", "T7"],
                "total_duration_days": 42.0,
                "zero_slack_tasks": ["T1", "T3", "T7"],
                "highest_slack_tasks": ["T2", "T5"],
                "staffing_implication": "Backend Developer must be dedicated.",
            },
            "phases": [
                {"phase_number": 1, "name": "Discovery & Design", "duration_weeks": 1.5,
                 "percentage_of_total": 12.0, "milestones": ["Requirements finalized"],
                 "tasks": [{"id": "T1", "name": "Write API specs", "phase": 1,
                             "effort_hours": 12.0, "owner_role": "Backend Developer",
                             "dependencies": [], "risk_flag": False,
                             "critical_path": True, "slack_days": 0,
                             "definition_of_done": "Spec approved by tech lead"}]},
                {"phase_number": 2, "name": "Core Development", "duration_weeks": 4.5,
                 "percentage_of_total": 38.0, "milestones": ["Core features implemented"], "tasks": []},
                {"phase_number": 3, "name": "Integration & Edge Cases", "duration_weeks": 2.5,
                 "percentage_of_total": 22.0, "milestones": ["All integrations tested"], "tasks": []},
                {"phase_number": 4, "name": "QA & Testing", "duration_weeks": 2.5,
                 "percentage_of_total": 20.0, "milestones": ["UAT completed"], "tasks": []},
                {"phase_number": 5, "name": "Deployment & Handoff", "duration_weeks": 1.0,
                 "percentage_of_total": 8.0, "milestones": ["Production deployment"], "tasks": []},
            ],
        },
        "use_case_task_mapping": {"UC1": ["T1"], "UC2": ["T3"]},
    }


@pytest.fixture
def stub_risk_register():
    return {
        "risk_register": [
            {"id": "R1", "category": "Technical", "description": "If Snowflake API changes, pipeline breaks",
             "probability": "MEDIUM", "impact": "HIGH", "score": "HIGH",
             "trigger": "Snowflake deprecation notice", "mitigation": "Pin API version",
             "contingency": "Fall back to direct DB query"},
        ],
        "risk_use_case_mapping": {"R1": ["UC2"]},
        "critical_path_risk_flags": ["T1"],
    }


@pytest.fixture
def stub_staffing_plan():
    return {
        "staffing_plan": [
            {"role": "Backend Developer", "phase_involvement": [1, 2, 3],
             "total_hours": 240.0, "allocation_percent": 75.0,
             "skills_required": ["Python", "FastAPI", "Snowflake"],
             "critical_path": True, "notes": "Owns critical path tasks"},
            {"role": "QA Engineer", "phase_involvement": [3, 4],
             "total_hours": 80.0, "allocation_percent": 50.0,
             "skills_required": ["Pytest", "API testing"],
             "critical_path": False, "notes": ""},
        ],
        "open_questions": [
            {"priority": 1, "question": "Who owns the Snowflake connection credentials?",
             "urgency": "Before build", "impact_if_unanswered": "Integration blocked"},
        ],
        "pm_confidence_score": {"score": 72.0, "deductions": [{"amount": 5.0, "reason": "1 assumption"}],
                                 "interpretation": "PM confidence score is 72.0 because one assumption logged."},
        "project_viability": None,
        "actor_role_mapping": {"A1": ["Backend Developer", "QA Engineer"]},
    }
