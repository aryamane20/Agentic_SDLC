"""
PM Digital Twin — Agent Runner
Handles retry logic, validation, and fallback strategies.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from agent.logger import PMReportLogger
from agent.validator import SchemaValidator
from agent.viability_checker import check_viability


class AgentRunner:
    """
    Runs the PM agent with retry logic, validation, and fallback strategies.
    """

    def __init__(
        self,
        agent,
        logger: Optional[PMReportLogger] = None,
        validator: Optional[SchemaValidator] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.agent = agent
        self.logger = logger or PMReportLogger()
        self.validator = validator or SchemaValidator()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def run_with_retry(
        self,
        raw_input: str,
        input_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the agent with automatic retry on failure.

        Args:
            raw_input: Raw project requirements text
            input_source: Optional source identifier

        Returns:
            dict with 'report', 'success', 'attempts', 'error' keys
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.time()
                
                # Run the agent
                result = self.agent.run(raw_input)
                runtime = time.time() - start_time
                
                # Add metadata
                result["input_source"] = input_source
                result["runtime_seconds"] = runtime
                result["attempt"] = attempt
                
                # Log the result
                self.logger.log_report(
                    result["report"],
                    metadata={
                        "input_source": input_source,
                        "runtime_seconds": runtime,
                        "tokens_used": result.get("tokens_used"),
                        "cache_read_tokens": result.get("cache_read_tokens", 0),
                        "cache_creation_tokens": result.get("cache_creation_tokens", 0),
                        "attempt": attempt
                    }
                )
                
                return {
                    "report": result["report"],
                    "raw_output": result.get("raw_output"),
                    "success": True,
                    "attempts": attempt,
                    "error": None,
                    "tokens_used": result.get("tokens_used"),
                    "cache_read_tokens": result.get("cache_read_tokens", 0),
                    "cache_creation_tokens": result.get("cache_creation_tokens", 0),
                    "runtime_seconds": runtime
                }
                
            except Exception as e:
                last_error = e
                logging.warning(f"Attempt {attempt} failed: {str(e)}")
                
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)  # Exponential backoff
                    continue
                
                # Log the error
                self.logger.log_error(
                    e,
                    context={
                        "input_source": input_source,
                        "attempt": attempt,
                        "raw_input": raw_input[:500]  # Truncate for log
                    }
                )
        
        return {
            "report": None,
            "raw_output": None,
            "success": False,
            "attempts": self.max_retries,
            "error": str(last_error),
            "tokens_used": 0,
            "runtime_seconds": 0
        }

    def run_with_validation(
        self,
        raw_input: str,
        input_source: Optional[str] = None,
        validate_output: bool = True,
        check_viability_flag: bool = True
    ) -> Dict[str, Any]:
        """
        Run the agent and validate output against schema.

        Args:
            raw_input: Raw project requirements text
            input_source: Optional source identifier
            validate_output: Whether to validate the output
            check_viability_flag: Whether to run viability check (default True)

        Returns:
            dict with 'report', 'validation_result', 'success', 'viability_result' keys
        """
        # First run with retry
        result = self.run_with_retry(raw_input, input_source)
        
        if not result["success"]:
            return {
                "report": None,
                "validation_result": None,
                "success": False,
                "error": result["error"],
                "viability_result": None
            }
        
        # Validate if requested
        validation_result = None
        if validate_output:
            validation_result = self.validator.validate(result["report"])
        
        # Run viability check if requested
        viability_result = None
        if check_viability_flag and result["report"]:
            viability_result = check_viability(raw_input, result["report"])
            # Add viability to report if constraints were provided
            if viability_result:
                result["report"]["project_viability"] = viability_result
        
        return {
            "report": result["report"],
            "raw_output": result.get("raw_output"),
            "validation_result": validation_result,
            "viability_result": viability_result,
            "success": validation_result is None or validation_result.get("valid", False),
            "attempts": result["attempts"],
            "tokens_used": result.get("tokens_used"),
            "cache_read_tokens": result.get("cache_read_tokens", 0),
            "cache_creation_tokens": result.get("cache_creation_tokens", 0),
            "runtime_seconds": result.get("runtime_seconds")
        }

    def run_with_fallback(
        self,
        raw_input: str,
        input_source: Optional[str] = None,
        fallback_versions: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Run the agent with fallback to different prompt versions if needed.

        Args:
            raw_input: Raw project requirements text
            input_source: Optional source identifier
            fallback_versions: List of prompt versions to try (e.g., ['v1', 'v2'])

        Returns:
            dict with 'report', 'success', 'prompt_version_used', 'error' keys
        """
        versions_to_try = fallback_versions or [self.agent.prompt_version]
        last_error = None
        
        for version in versions_to_try:
            try:
                # Update agent's prompt version
                self.agent.prompt_version = version
                self.agent.system_prompt = self.agent._build_system_context()
                
                # Try running
                result = self.run_with_retry(raw_input, input_source)
                
                if result["success"]:
                    result["prompt_version_used"] = version
                    return result
                
                last_error = result["error"]
                
            except Exception as e:
                last_error = e
                continue
        
        return {
            "report": None,
            "raw_output": None,
            "success": False,
            "prompt_version_used": None,
            "error": last_error or "All fallback versions failed",
            "tokens_used": 0,
            "runtime_seconds": 0
        }
