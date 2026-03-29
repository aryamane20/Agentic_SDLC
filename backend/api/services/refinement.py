"""
Refinement — ARCHITECTURE target: re-run Steps 5–8 only with 1–4 locked.

MVP: multi-turn Messages API — user (brief) → assistant (compact prior JSON, cache_control) →
user (feedback). Stripped sections save tokens; merge_locked_sections_from_prior restores Steps
1–4 after the call. Trace cache_read_tokens / cache_creation_tokens on repeat refinements.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from agent.main import PMAgent

from backend.api.services.approval_gate import evaluate_gate

# Stripped from LLM input — merged back from previous_report after the call (Steps 1–4).
LOCKED_SECTIONS = frozenset({"project_understanding", "assumption_log"})

# Intake / classification — must match prior report after refine (Steps 1–4).
_CLASSIFICATION_META_KEYS = (
    "input_quality",
    "project_type",
    "classification_confidence",
    "sdlc_approach",
    "sdlc_rationale",
)


def _strip_and_compact(report: dict[str, Any]) -> str:
    """Omit sections overwritten by merge; compact JSON (no indent) to save tokens."""
    stripped = {k: v for k, v in report.items() if k not in LOCKED_SECTIONS}
    meta = stripped.get("report_metadata")
    if isinstance(meta, dict):
        stripped["report_metadata"] = {
            k: v for k, v in meta.items() if k not in _CLASSIFICATION_META_KEYS
        }
    return json.dumps(stripped, ensure_ascii=False, separators=(",", ":"))


def merge_locked_sections_from_prior(previous_report: dict[str, Any], new_report: dict[str, Any]) -> dict[str, Any]:
    """Preserve extraction + classification; allow plan / risks / staffing / viability to update."""
    merged = copy.deepcopy(new_report)
    for key in LOCKED_SECTIONS:
        if key in previous_report:
            merged[key] = copy.deepcopy(previous_report[key])
    prev_meta = previous_report.get("report_metadata")
    new_meta = merged.get("report_metadata")
    if isinstance(prev_meta, dict) and isinstance(new_meta, dict):
        meta = copy.deepcopy(new_meta)
        for k in _CLASSIFICATION_META_KEYS:
            if k in prev_meta:
                meta[k] = copy.deepcopy(prev_meta[k])
        merged["report_metadata"] = meta
    return merged


def build_refinement_messages(
    original_brief: str,
    previous_report: dict[str, Any],
    feedback: str,
) -> list[dict[str, Any]]:
    """
    Three-turn thread for refinement (Anthropic Messages API).

    Assistant turn is plain JSON text with ephemeral cache_control for provider-side prefix cache.
    Steps 1–4 are omitted from the JSON; merged server-side after the call.
    """
    compact_prior = _strip_and_compact(previous_report)
    return [
        {
            "role": "user",
            "content": (
                "PROJECT REQUIREMENTS (original brief, unchanged):\n"
                f"---\n{original_brief}\n---"
            ),
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": compact_prior,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        },
        {
            "role": "user",
            "content": (
                "[PM REFINEMENT — revise the full report using your prior JSON response as the baseline]\n\n"
                "PM FEEDBACK:\n"
                f"{feedback}\n\n"
                "Output a single valid JSON object only (full PM digital twin report, same schema). "
                "No prose. No markdown code fences. Just the JSON."
            ),
        },
    ]


def run_refinement(
    *,
    agent: PMAgent,
    original_brief: str,
    previous_report: dict,
    feedback: str,
) -> dict:
    messages = build_refinement_messages(original_brief, previous_report, feedback)
    result = agent.run_with_history(messages, input_source="backend-refine")
    merged = merge_locked_sections_from_prior(previous_report, result["report"])
    result["report"] = merged
    result["gate"] = evaluate_gate(merged).model_dump(mode="json")
    return result
