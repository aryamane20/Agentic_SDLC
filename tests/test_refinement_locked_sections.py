"""Steps 1–4 merge after refinement — deterministic lock without live LLM."""

import json

from backend.api.services.refinement import (
    _strip_and_compact,
    build_refinement_messages,
    merge_locked_sections_from_prior,
)


def test_build_refinement_messages_three_turns_and_cache_block():
    brief = "Build a portal."
    prior = {
        "project_understanding": {"x": 1},
        "assumption_log": [],
        "report_metadata": {"input_quality": "HIGH", "generated_at": "2026-01-01"},
        "project_plan": {"phases": []},
    }
    msgs = build_refinement_messages(brief, prior, "Shorten timeline.")
    assert len(msgs) == 3
    assert msgs[0]["role"] == "user" and brief in str(msgs[0]["content"])
    assert msgs[1]["role"] == "assistant"
    blocks = msgs[1]["content"]
    assert isinstance(blocks, list) and blocks[0]["type"] == "text"
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    parsed = json.loads(blocks[0]["text"])
    assert "project_understanding" not in parsed
    assert "project_plan" in parsed
    assert msgs[2]["role"] == "user" and "Shorten timeline." in str(msgs[2]["content"])


def test_strip_and_compact_omits_locked_sections_and_classification_meta():
    prior = {
        "project_understanding": {"keep": False},
        "assumption_log": [],
        "report_metadata": {
            "input_quality": "HIGH",
            "project_type": "T",
            "classification_confidence": "H",
            "sdlc_approach": "Predictive",
            "sdlc_rationale": "r",
            "generated_at": "2026-01-01",
        },
        "project_plan": {"phases": [{"name": "p1"}]},
    }
    s = _strip_and_compact(prior)
    assert "\n" not in s or s.count("\n") == 0
    data = json.loads(s)
    assert "project_understanding" not in data
    assert "assumption_log" not in data
    assert data["project_plan"] == prior["project_plan"]
    meta = data["report_metadata"]
    assert "input_quality" not in meta
    assert meta.get("generated_at") == "2026-01-01"


def test_merge_restores_extraction_and_classification():
    prior = {
        "project_understanding": {"primary_goal": "A", "beneficiary": "B"},
        "assumption_log": [{"id": "A1", "what": "x"}],
        "report_metadata": {
            "input_quality": "HIGH",
            "project_type": "TYPE_A",
            "classification_confidence": "HIGH",
            "sdlc_approach": "Predictive",
            "sdlc_rationale": "locked rationale",
            "pm_confidence_score": 70.0,
        },
        "project_plan": {"phases": []},
    }
    new = {
        "project_understanding": {"primary_goal": "CHANGED", "beneficiary": "oops"},
        "assumption_log": [],
        "report_metadata": {
            "input_quality": "LOW",
            "project_type": "TYPE_F",
            "classification_confidence": "LOW",
            "sdlc_approach": "Adaptive",
            "sdlc_rationale": "new wrong",
            "pm_confidence_score": 90.0,
            "generated_at": "2026-01-02",
        },
        "project_plan": {"phases": [{"name": "build"}]},
    }
    m = merge_locked_sections_from_prior(prior, new)
    assert m["project_understanding"] == prior["project_understanding"]
    assert m["assumption_log"] == prior["assumption_log"]
    meta = m["report_metadata"]
    assert meta["input_quality"] == "HIGH"
    assert meta["project_type"] == "TYPE_A"
    assert meta["classification_confidence"] == "HIGH"
    assert meta["sdlc_approach"] == "Predictive"
    assert meta["sdlc_rationale"] == "locked rationale"
    # LLM may refresh confidence / timestamp — not part of Steps 1–4 lock
    assert meta["pm_confidence_score"] == 90.0
    assert meta["generated_at"] == "2026-01-02"
    assert m["project_plan"] == new["project_plan"]
