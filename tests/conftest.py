"""
Pytest configuration and fixtures for PM Digital Twin tests.
"""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path

from agent.main import PMAgent
from agent.runner import AgentRunner
from agent.logger import PMReportLogger
from agent.validator import SchemaValidator
from schemas.input_schema import PMInput


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing without API calls."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text='{"report": "test"}')]
    mock_response.usage = Mock(
        input_tokens=100,
        output_tokens=200,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0
    )
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def agent(mock_anthropic_client):
    """Create a PMAgent instance with mocked client."""
    agent = PMAgent(prompt_version="v1.6")
    agent.client = mock_anthropic_client
    return agent


@pytest.fixture
def runner(agent):
    """Create an AgentRunner instance."""
    return AgentRunner(agent=agent)


@pytest.fixture
def logger(tmp_path):
    """Create a PMReportLogger with temporary directory."""
    log_dir = tmp_path / "logs"
    return PMReportLogger(log_dir=str(log_dir))


@pytest.fixture
def validator():
    """Create a SchemaValidator instance."""
    return SchemaValidator()


@pytest.fixture
def sample_valid_input():
    """Sample valid project requirements input."""
    return """
    Build an internal dashboard for the data analytics team.
    The dashboard should display real-time metrics for data pipelines.
    It needs to integrate with our existing Snowflake database.
    Timeline: 3 months. Budget: $50k.
    Team: 2 backend engineers, 1 frontend engineer, 1 PM.
    """


@pytest.fixture
def sample_invalid_input():
    """Sample invalid/malformed input."""
    return "Build something cool."  # Too short


@pytest.fixture
def sample_test_cases():
    """Load sample test cases from inputs directory."""
    test_cases_dir = Path(__file__).parent.parent / "inputs" / "test-cases"
    test_cases = {}
    
    if test_cases_dir.exists():
        for tc_file in sorted(test_cases_dir.glob("tc-*.txt")):
            test_cases[tc_file.stem] = tc_file.read_text()
    
    return test_cases


@pytest.fixture
def mock_api_failure():
    """Mock API failure scenario."""
    def _mock_failure(*args, **kwargs):
        raise Exception("API rate limit exceeded")
    return _mock_failure
