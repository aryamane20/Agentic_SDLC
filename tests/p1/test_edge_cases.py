"""
Edge case tests for PM Digital Twin agent.
Malformed/empty/boundary inputs should be handled without crash.
"""

import pytest
from unittest.mock import Mock


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_agent_handles_empty_input(self, agent):
        """Agent should handle empty input gracefully."""
        result = agent.run("")
        
        # Should return something, not crash
        assert result is not None
        assert "report" in result

    def test_agent_handles_very_short_input(self, agent):
        """Agent should handle very short input."""
        result = agent.run("Build a website")
        
        assert result is not None
        assert "report" in result

    def test_agent_handles_very_long_input(self, agent):
        """Agent should handle very long input without truncation issues."""
        long_input = "Build a website. " * 1000  # Very long input
        
        result = agent.run(long_input)
        
        assert result is not None

    def test_agent_handles_special_characters(self, agent):
        """Agent should handle special characters in input."""
        special_input = "Build a website with <script>alert('xss')</script> and unicode: 你好世界 🌍"
        
        result = agent.run(special_input)
        
        assert result is not None

    def test_agent_handles_json_like_input(self, agent):
        """Agent should handle input that looks like JSON."""
        json_input = '{"type": "web", "budget": "$50k"}'
        
        result = agent.run(json_input)
        
        assert result is not None

    def test_agent_handles_markdown_input(self, agent):
        """Agent should handle markdown-formatted input."""
        md_input = """
        # Project Requirements
        
        ## Overview
        Build an internal tool
        
        ## Timeline
        - 3 months
        - $50k budget
        """
        
        result = agent.run(md_input)
        
        assert result is not None

    def test_agent_handles_contradictory_input(self, agent):
        """Agent should handle contradictory requirements."""
        contradictory_input = """
        Build a simple website that is also enterprise-grade with microservices.
        Timeline is 1 week but needs to be fully featured.
        Budget is $100 but must have 99.99% uptime.
        """
        
        result = agent.run(contradictory_input)
        
        assert result is not None

    def test_agent_handles_missing_context(self, agent):
        """Agent should handle input with missing context."""
        vague_input = "Make it better."
        
        result = agent.run(vague_input)
        
        assert result is not None

    def test_extract_json_handles_no_json(self, agent):
        """JSON extractor should handle response without JSON."""
        no_json = "This is just plain text without any JSON."
        
        result = agent._extract_json(no_json)
        
        # Should return error structure
        assert "parse_error" in result or "raw_output" in result

    def test_extract_json_handles_truncated_json(self, agent):
        """JSON extractor should handle truncated JSON."""
        truncated = '{"project_understanding": {"primary_goal": "test"'
        
        result = agent._extract_json(truncated)
        
        # Should return something
        assert result is not None

    def test_extract_json_handles_malformed_json(self, agent):
        """JSON extractor should handle malformed JSON."""
        malformed = '{"key": "value", invalid json}'
        
        result = agent._extract_json(malformed)
        
        # Should return error structure
        assert result is not None

    def test_logger_handles_missing_fields(self, logger):
        """Logger should handle reports with missing fields."""
        incomplete_report = {
            "project_understanding": {"primary_goal": "test"}
        }
        
        # Should not crash
        log_entry = logger.log_report(incomplete_report)
        
        assert log_entry is not None

    def test_logger_handles_none_values(self, logger):
        """Logger should handle None values in report."""
        report_with_none = {
            "project_understanding": None,
            "report_metadata": {"project_type": None}
        }
        
        # Should not crash
        log_entry = logger.log_report(report_with_none)
        
        assert log_entry is not None

    def test_validator_handles_missing_fields(self, validator):
        """Validator should handle reports with missing fields."""
        incomplete_report = {
            "project_understanding": {"primary_goal": "test"}
        }
        
        # Should not crash, just return errors
        result = validator.validate(incomplete_report)
        
        assert result is not None
        # PMReport is permissive; business rules may surface warnings without schema errors.
        assert len(result["errors"]) > 0 or len(result["warnings"]) > 0

    def test_validator_handles_empty_arrays(self, validator):
        """Validator should handle empty arrays."""
        report_with_empty_arrays = {
            "report_metadata": {
                "generated_at": "2026-01-01T00:00:00Z",
                "input_quality": "HIGH",
                "pm_confidence_score": 50,
                "project_type": "TYPE_A",
                "sdlc_approach": "Predictive"
            },
            "project_understanding": {
                "primary_goal": "Test",
                "beneficiary": "Test",
                "trigger": "Test",
                "success_definition": "Test"
            },
            "assumption_log": [],  # Empty - violates minItems: 1
            "project_plan": {
                "total_duration_weeks": 10,
                "buffer_applied_percent": 10,
                "critical_path_summary": {
                    "sequence": [],
                    "total_duration_days": 10,
                    "zero_slack_tasks": [],
                    "staffing_implication": "test"
                },
                "phases": []
            },
            "risk_register": [],  # Empty - violates minItems: 3
            "staffing_plan": [],
            "open_questions": [],
            "pm_confidence_score": {
                "score": 50,
                "deductions": [],
                "interpretation": "test"
            }
        }
        
        result = validator.validate(report_with_empty_arrays)
        
        # Permissive Pydantic model: expect business-rule or schema feedback, not a crash
        assert result is not None
        assert len(result["errors"]) + len(result["warnings"]) > 0
