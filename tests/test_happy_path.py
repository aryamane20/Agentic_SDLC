"""
Happy path tests for PM Digital Twin agent.
Valid input should produce expected output format.
"""

from unittest.mock import Mock


class TestHappyPath:
    """Test valid inputs produce expected output format."""

    def test_agent_run_returns_dict(self, agent, sample_valid_input):
        """Agent run should return a dict with expected keys."""
        result = agent.run(sample_valid_input)
        
        assert isinstance(result, dict)
        assert "report" in result
        assert "tokens_used" in result

    def test_agent_run_parses_json(self, agent, sample_valid_input):
        """Agent should parse JSON from LLM response."""
        # Create a mock response with valid JSON
        mock_response = Mock()
        mock_response.content = [Mock(text='{"project_understanding": {"primary_goal": "test"}, "report_metadata": {"generated_at": "2026-01-01"}}')]
        mock_response.usage = Mock(input_tokens=100, output_tokens=200)
        
        original_create = agent.client.messages.create
        agent.client.messages.create = Mock(return_value=mock_response)
        
        result = agent.run(sample_valid_input, use_cache=False)
        
        assert isinstance(result["report"], dict)
        assert "project_understanding" in result["report"]
        
        # Restore
        agent.client.messages.create = original_create

    def test_runner_run_with_retry_success(self, runner, sample_valid_input):
        """Runner should succeed on first try with valid input."""
        result = runner.run_with_retry(sample_valid_input, input_source="test")
        
        assert result["success"] is True
        assert result["attempts"] == 1
        assert result["report"] is not None

    def test_runner_run_with_validation_valid(self, runner, sample_valid_input):
        """Runner with validation should pass for valid output."""
        result = runner.run_with_validation(sample_valid_input, validate_output=False)
        
        assert result["success"] is True
        assert result["report"] is not None

    def test_logger_logs_report(self, logger, sample_valid_input):
        """Logger should log reports without error."""
        mock_report = {
            "project_understanding": {"primary_goal": "test"},
            "report_metadata": {"project_type": "TYPE_A", "sdlc_approach": "Predictive"},
            "project_plan": {"phases": []},
            "risk_register": [],
            "assumption_log": [],
            "staffing_plan": [],
            "open_questions": [],
            "pm_confidence_score": {"score": 80}
        }
        
        metadata = {"input_source": "test", "runtime_seconds": 1.0}
        
        log_entry = logger.log_report(mock_report, metadata)
        
        assert log_entry is not None
        assert log_entry["input_source"] == "test"

    def test_schema_validator_validates_valid_report(self, validator):
        """Validator should pass for valid report."""
        valid_report = {
            "report_metadata": {
                "generated_at": "2026-01-01T00:00:00Z",
                "input_quality": "HIGH",
                "pm_confidence_score": 85,
                "project_type": "TYPE_A",
                "sdlc_approach": "Predictive"
            },
            "project_understanding": {
                "primary_goal": "Build internal dashboard",
                "beneficiary": "Data team",
                "trigger": "Need for metrics",
                "success_definition": "Dashboard live"
            },
            "assumption_log": [
                {
                    "id": "A1",
                    "what": "Test assumption",
                    "why": "Because",
                    "pmi_basis": "PMBOK",
                    "risk_if_wrong": "MEDIUM",
                    "consequence": "Delay"
                }
            ],
            "project_plan": {
                "total_duration_weeks": 12,
                "buffer_applied_percent": 10,
                "critical_path_summary": {
                    "sequence": ["T1", "T2"],
                    "total_duration_days": 30,
                    "zero_slack_tasks": ["T1"],
                    "staffing_implication": "Need senior dev"
                },
                "phases": [
                    {
                        "phase_number": 1,
                        "name": "Init",
                        "duration_weeks": 2,
                        "percentage_of_total": 18,
                        "milestones": ["M1", "M2"],
                        "tasks": []
                    },
                    {
                        "phase_number": 2,
                        "name": "Plan",
                        "duration_weeks": 2,
                        "percentage_of_total": 18,
                        "milestones": ["M1"],
                        "tasks": []
                    },
                    {
                        "phase_number": 3,
                        "name": "Build",
                        "duration_weeks": 4,
                        "percentage_of_total": 30,
                        "milestones": ["M1"],
                        "tasks": []
                    },
                    {
                        "phase_number": 4,
                        "name": "Test",
                        "duration_weeks": 2,
                        "percentage_of_total": 24,
                        "milestones": ["M1"],
                        "tasks": []
                    },
                    {
                        "phase_number": 5,
                        "name": "Deploy",
                        "duration_weeks": 2,
                        "percentage_of_total": 10,
                        "milestones": ["M1"],
                        "tasks": []
                    }
                ]
            },
            "risk_register": [
                {
                    "id": "R1",
                    "category": "Technical",
                    "description": "Risk description",
                    "probability": "MEDIUM",
                    "impact": "HIGH",
                    "score": "HIGH",
                    "trigger": "Trigger condition",
                    "mitigation": "Mitigation action",
                    "contingency": "Contingency plan"
                },
                {
                    "id": "R2",
                    "category": "Schedule",
                    "description": "Schedule risk",
                    "probability": "LOW",
                    "impact": "MEDIUM",
                    "score": "LOW",
                    "trigger": "Delay",
                    "mitigation": "Add buffer",
                    "contingency": "Adjust scope"
                },
                {
                    "id": "R3",
                    "category": "Resource",
                    "description": "Resource risk",
                    "probability": "MEDIUM",
                    "impact": "MEDIUM",
                    "score": "MEDIUM",
                    "trigger": "Resource unavailable",
                    "mitigation": "Cross-train",
                    "contingency": "Hire contractor"
                }
            ],
            "staffing_plan": [
                {
                    "role": "Backend Engineer",
                    "phase_involvement": [1, 2, 3, 4, 5],
                    "total_hours": 200,
                    "allocation_percent": 45,
                    "skills_required": ["Python", "SQL"],
                    "critical_path": True
                },
                {
                    "role": "QA Engineer",
                    "phase_involvement": [3, 4],
                    "total_hours": 50,
                    "allocation_percent": 12,
                    "skills_required": ["Testing"],
                    "critical_path": False
                }
            ],
            "open_questions": [
                {
                    "priority": 1,
                    "question": "What is the exact data source?",
                    "urgency": "Before build",
                    "impact_if_unanswered": "Cannot design schema"
                }
            ],
            "pm_confidence_score": {
                "score": 85,
                "deductions": [],
                "interpretation": "Good confidence"
            }
        }
        
        result = validator.validate(valid_report)
        
        # Valid report should have no errors
        assert result["valid"] is True
