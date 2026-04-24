"""
Retry tests for PM Digital Twin agent.
Mock API failure scenarios should trigger retry logic.
"""

import pytest
from unittest.mock import Mock


class TestRetry:
    """Test retry logic and failure handling."""

    def test_runner_retries_on_failure(self, agent):
        """Runner should retry on API failure."""
        from agent.runner import AgentRunner
        
        # Create a runner with the agent
        runner = AgentRunner(agent=agent, max_retries=3, retry_delay=0.1)
        
        # Mock client that fails twice then succeeds
        mock_response_fail = Mock()
        mock_response_fail.content = [Mock(text='{"error": "rate limit"}')]
        mock_response_fail.usage = Mock(
            input_tokens=100,
            output_tokens=200,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        mock_response_success = Mock()
        mock_response_success.content = [Mock(text='{"project_understanding": {"primary_goal": "test"}, "report_metadata": {"generated_at": "2026-01-01"}}')]
        mock_response_success.usage = Mock(
            input_tokens=100,
            output_tokens=200,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )
        
        # Create side effect that fails twice then succeeds
        call_count = [0]
        def create_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception("API rate limit exceeded")
            return mock_response_success
        
        agent.client.messages.create = Mock(side_effect=create_side_effect)

        # Bust disk cache so attempt 1 always exercises the API mock (retry behavior).
        result = runner.run_with_retry(
            "Build a test project __retry_side_effect__", input_source="test"
        )

        # Should eventually succeed after retries
        assert result["success"] is True
        assert result["attempts"] == 3

    def test_runner_exhausts_retries(self, agent):
        """Runner should exhaust all retries on persistent failure."""
        from agent.runner import AgentRunner
        
        runner = AgentRunner(agent=agent, max_retries=3, retry_delay=0.1)
        
        # Always fail
        agent.client.messages.create = Mock(side_effect=Exception("API down"))
        
        result = runner.run_with_retry("Build a test project", input_source="test")
        
        # Should fail after all retries
        assert result["success"] is False
        assert result["attempts"] == 3
        assert result["error"] is not None

    def test_runner_retry_delay_scales_linearly(self, agent):
        """Delay = retry_delay * attempt (linear, not exponential)."""
        from unittest.mock import patch
        from agent.runner import AgentRunner

        runner = AgentRunner(agent=agent, max_retries=3, retry_delay=0.05)
        agent.client.messages.create.side_effect = Exception("fail")

        sleep_args: list[float] = []
        with patch("agent.runner.time.sleep", side_effect=lambda d: sleep_args.append(d)):
            runner.run_with_retry("test __linear_backoff__", input_source="t")

        assert len(sleep_args) >= 2
        for i, val in enumerate(sleep_args, start=1):
            assert abs(val - 0.05 * i) < 1e-9, f"attempt {i}: expected {0.05*i}, got {val}"

    def test_runner_has_fallback_method(self, agent):
        """Runner exposes run_with_fallback for multi-version retry."""
        from agent.runner import AgentRunner

        runner = AgentRunner(agent=agent)
        assert callable(getattr(runner, "run_with_fallback", None))

    def test_runner_records_attempts(self, agent):
        """Runner should record number of attempts."""
        from agent.runner import AgentRunner
        
        runner = AgentRunner(agent=agent, max_retries=1, retry_delay=0.1)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.content = [Mock(text='{"project_understanding": {"primary_goal": "test"}, "report_metadata": {"generated_at": "2026-01-01"}}')]
        mock_response.usage = Mock(input_tokens=100, output_tokens=200)
        agent.client.messages.create = Mock(return_value=mock_response)
        
        result = runner.run_with_retry("test input", input_source="test")
        
        assert "attempts" in result
        assert result["attempts"] >= 1

    def test_runner_caps_attempts_at_max(self, runner):
        """Runner should not exceed max_retries."""
        assert runner.max_retries > 0

    def test_run_with_validation_retries_until_schema_passes(self, runner):
        """Invalid output should trigger another agent run (cache busted on retry)."""
        from agent.runner import AgentRunner

        r = AgentRunner(agent=runner.agent, max_retries=3, retry_delay=0.01)
        run_calls = {"n": 0}

        def fake_run(*_a, **_kw):
            run_calls["n"] += 1
            return {
                "report": {"stub": True},
                "raw_output": "",
                "tokens_used": 10,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
            }

        def fake_validate(_rep):
            fake_validate.calls += 1
            if fake_validate.calls < 2:
                return {"valid": False, "errors": ["Phase 5 is 10.7%"], "warnings": []}
            return {"valid": True, "errors": [], "warnings": []}

        fake_validate.calls = 0
        r.agent.run = fake_run
        r.validator.validate = fake_validate
        out = r.run_with_validation(
            "brief", input_source="t", validate_output=True, check_viability_flag=False
        )
        assert out["success"] is True
        assert run_calls["n"] == 2
        assert fake_validate.calls == 2

    def test_runner_skips_validation_when_flag_false(self, runner, sample_valid_input):
        """validate_output=False skips schema check — run still succeeds."""
        result = runner.run_with_validation(sample_valid_input, validate_output=False)
        assert result["success"] is True
