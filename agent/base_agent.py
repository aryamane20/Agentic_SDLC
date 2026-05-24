"""
BaseAgent — shared foundation for all P3 sub-agents.

Each specialist agent (Intake, Planning, Risk, Staffing, Synthesis, Use Case)
is a thin subclass that overrides _build_user_message() and sets its own
prompt path, model, and max_tokens.

Key differences from PMAgent (agent/main.py):
  - No disk cache: orchestrator handles checkpointing between stages
  - No _enforce_hard_caps: Synthesis agent is responsible for post-processing
  - Per-agent prompt file instead of a single monolithic v1.6.4 system prompt
  - Both sync run() and async run_async() for the parallel Planning+Risk step
  - KB content injected via context["_kb_content"] by the orchestrator
  - _extract_json() relaxed to accept any partial schema (not just PMReport)
"""

from __future__ import annotations

import json
import os
import re
import time
from abc import abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import anthropic
from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()

MODEL_HAIKU  = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-20250514"

_MAX_RETRIES = 2   # retries on parse failure (3 total attempts)


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class BaseAgent:
    """
    Shared base for all P3 sub-agents.

    Subclasses must implement:
      _build_user_message(context: dict) -> str

    Subclasses may override:
      _is_valid_artifact(parsed: dict) -> bool   (default: non-empty dict)
    """

    def __init__(
        self,
        *,
        agent_name: str,
        prompt_path: Path,
        model: str = MODEL_HAIKU,
        max_tokens: int = 4000,
        temperature: float = 0.0,
    ) -> None:
        self.agent_name = agent_name
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._system_prompt = prompt_path.read_text(encoding="utf-8")
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.async_client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.langfuse = Langfuse()  # no-ops if LANGFUSE_* env vars are missing

    # ------------------------------------------------------------------
    # System prompt assembly
    # ------------------------------------------------------------------

    def _build_system_blocks(self, kb_content: Optional[str] = None) -> list[dict]:
        """
        Returns the system message block list for the Messages API.

        Both the agent prompt and the KB block (if provided) are marked with
        cache_control: ephemeral. They are identical across all requests to
        the same agent, so they get cache hits after the first call.
        """
        blocks: list[dict] = [
            {
                "type": "text",
                "text": self._system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        if kb_content:
            blocks.append(
                {
                    "type": "text",
                    "text": f"---KNOWLEDGE BASE---\n{kb_content}\n---END KNOWLEDGE BASE---",
                    "cache_control": {"type": "ephemeral"},
                }
            )
        return blocks

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def _build_user_message(self, context: dict) -> str:
        """
        Build the user-turn message for this agent.
        context contains the upstream artifacts + raw_brief + _kb_content.
        """

    def _is_valid_artifact(self, parsed: dict) -> bool:
        """
        Return True if the parsed JSON looks like a valid artifact for this agent.
        Default: any non-empty dict without a top-level 'error' key.
        Subclasses can override to require specific keys.
        """
        return isinstance(parsed, dict) and len(parsed) >= 1 and not parsed.get("parse_error")

    # ------------------------------------------------------------------
    # JSON extraction (battle-tested logic from PMAgent, relaxed for partials)
    # ------------------------------------------------------------------

    def _extract_json(self, raw_output: str) -> dict:
        """
        Extract the JSON artifact from the LLM response.

        Strategies (in order):
          1. JSON inside a ```json ... ``` code block
          2. Last large { ... } block in the response
          3. Entire output treated as JSON
          4. Fallback: parse_error dict
        """
        # Strategy 1: code block
        code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
        if code_block:
            try:
                return json.loads(code_block.group(1))
            except json.JSONDecodeError:
                pass

        # Strategy 2: last large { ... } block
        for match in reversed(list(re.finditer(r"\{", raw_output))):
            candidate = raw_output[match.start():]
            try:
                parsed = json.loads(candidate)
                if self._is_valid_artifact(parsed):
                    return parsed
            except json.JSONDecodeError:
                fixed = self._fix_truncated_json(candidate)
                if fixed:
                    try:
                        parsed = json.loads(fixed)
                        if self._is_valid_artifact(parsed):
                            return parsed
                    except json.JSONDecodeError:
                        pass

        # Strategy 3: full output as JSON
        try:
            cleaned = raw_output.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
                cleaned = re.sub(r"```$", "", cleaned).strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        return {
            "parse_error": True,
            "raw_output": raw_output,
            "generated_at": _utc_iso_z(),
        }

    def _fix_truncated_json(self, json_str: str) -> Optional[str]:
        open_b = json_str.count("{")
        close_b = json_str.count("}")
        if open_b > close_b:
            return json_str + ("}" * (open_b - close_b))
        return None

    # ------------------------------------------------------------------
    # LLM call helpers
    # ------------------------------------------------------------------

    def _call_sync(self, system_blocks: list[dict], user_msg: str) -> tuple[dict, dict]:
        """Single synchronous LLM call. Returns (artifact, token_counts)."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_blocks,
            messages=[{"role": "user", "content": user_msg}],
        )
        return self._parse_response(response)

    async def _call_async(self, system_blocks: list[dict], user_msg: str) -> tuple[dict, dict]:
        """Single async LLM call. Returns (artifact, token_counts)."""
        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_blocks,
            messages=[{"role": "user", "content": user_msg}],
        )
        return self._parse_response(response)

    def _parse_response(self, response: Any) -> tuple[dict, dict]:
        """Extract artifact dict and token counts from an API response."""
        raw = response.content[0].text
        usage = response.usage
        tokens = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
            "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        }
        artifact = self._extract_json(raw)
        return artifact, tokens

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, *, context: dict) -> dict:
        """
        Synchronous agent run with parse-failure retry.

        Returns:
            {
                "artifact": dict,           # parsed partial output
                "raw_output": str,          # last raw LLM response
                "input_tokens": int,
                "output_tokens": int,
                "cache_read_tokens": int,
                "cache_creation_tokens": int,
                "parse_failed": bool,
                "attempts": int,
            }
        """
        kb_content = context.get("_kb_content")
        system_blocks = self._build_system_blocks(kb_content)
        user_msg = self._build_user_message(context)

        artifact: dict = {}
        tokens: dict = {}
        attempts = 0

        for attempt in range(_MAX_RETRIES + 1):
            attempts = attempt + 1
            artifact, tokens = self._call_sync(system_blocks, user_msg)
            if not artifact.get("parse_error"):
                break
            if attempt < _MAX_RETRIES:
                time.sleep(attempt + 1)

        parse_failed = bool(artifact.get("parse_error"))
        self._trace(context, artifact, tokens, parse_failed)

        return {
            "artifact": artifact,
            "raw_output": artifact.pop("raw_output", ""),
            "parse_failed": parse_failed,
            "attempts": attempts,
            **tokens,
        }

    async def run_async(self, *, context: dict) -> dict:
        """
        Async agent run with parse-failure retry.
        Used for the parallel Planning+Risk step in the orchestrator.
        Same return shape as run().
        """
        import asyncio

        kb_content = context.get("_kb_content")
        system_blocks = self._build_system_blocks(kb_content)
        user_msg = self._build_user_message(context)

        artifact: dict = {}
        tokens: dict = {}
        attempts = 0

        for attempt in range(_MAX_RETRIES + 1):
            attempts = attempt + 1
            artifact, tokens = await self._call_async(system_blocks, user_msg)
            if not artifact.get("parse_error"):
                break
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(attempt + 1)

        parse_failed = bool(artifact.get("parse_error"))
        self._trace(context, artifact, tokens, parse_failed)

        return {
            "artifact": artifact,
            "raw_output": artifact.pop("raw_output", ""),
            "parse_failed": parse_failed,
            "attempts": attempts,
            **tokens,
        }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _trace(self, context: dict, artifact: dict, tokens: dict, parse_failed: bool) -> None:
        """Record a Langfuse span for this agent call. No-ops if keys are missing."""
        try:
            self.langfuse.update_current_span(
                name=f"p3-{self.agent_name}",
                input={"brief_preview": str(context.get("raw_brief", ""))[:200]},
                output=artifact,
                metadata={
                    "agent": self.agent_name,
                    "model": self.model,
                    "parse_failed": parse_failed,
                    **tokens,
                },
            )
        except Exception:
            pass  # Langfuse failures must never crash the pipeline
