# Prompts Directory

This directory contains versioned system prompts for the PM Digital Twin agent.
Each version is stored as an immutable .txt file once committed.

## Active Versions

| Version | Theme | Key Changes |
|---------|-------|-------------|
| v1.0 | Baseline | Initial 8-step reasoning, role/KB separation |
| v1.1 | Reasoning Completeness | SDLC approach, NFR extraction, critical path + slack |
| v1.2 | Output Reliability | Confidence calibration, viability check, JSON skeleton, deduction table |
| v1.3 | Production Architecture | JSON-only output, scratchpad instruction, effort_hours cap |
| v1.4 | Haiku Compatibility | Budget risk category, priority caps, open_questions limit |
| v1.5 | Structural trim | Anti-patterns, tradeoff field, shorter prompt |
| v1.6 | Consistency + staffing + caps | Mechanical score rule, SDLC tie-breaker, staffing completeness, scratchpad removed |
| v1.6.1 | NFR materiality | Fewer spurious NFR assumptions; replay / comparison |
| v1.6.2 | Urgency + staffing + interpretation | Open-question rubric + per-role staffing assumptions; PM confidence interpretation lead-in; **default in code** |

## Archive

The `archive/` folder contains intermediate prompt versions (v1.0.0, v1.1.0, v1.2.0, v1.6.0) preserved for reproducibility of earlier eval results.

---

For full detailed changelog history, see `PROMPT_CHANGELOG.md`.
