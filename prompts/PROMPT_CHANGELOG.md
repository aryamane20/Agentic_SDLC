# PROMPT_CHANGELOG.md
## System Prompt Version History — PM Digital Twin

A prompt version is justified when there is a measurable before/after eval score
difference. Whitespace changes, comment tweaks, and one-line fixes are git commits,
not prompt versions.

Intermediate versions (v1.0.0–v1.6.1) are archived in `prompts/archive/`.
Active versions: v1.0 through v1.5.

---

## v1.0 — BASELINE
**File:** `prompts/v1.0_system.txt`
**Date:** March 2026
**Type:** Initial implementation

**What's in this version:**
- Full 8-step reasoning process (PMI/PMBOK grounded)
- Identity: Senior Internal Product PM, 8+ years experience
- Role/KB separation: reasoning prompt and domain knowledge maintained separately
- Hard output contract with JSON requirement (prose description, no skeleton)

**What consolidated from archive:**
- v1.0.0 — initial prompt
- v1.0.1 — role/KB separation (infrastructure change, zero reasoning change)

**Rubric scores:** D3=2.8/5 (established eval baseline)

---

## v1.1 — REASONING COMPLETENESS
**File:** `prompts/v1.1_system.txt`
**Date:** March 2026
**Type:** FUNCTIONAL — reasoning process additions

**What changed from v1.0:**
- Step 2 Part B: SDLC Approach classification (Predictive / Adaptive / Hybrid)
  with decision rules and downstream effects on phase structure
- Step 3: Non-Functional Requirements — six new fields (performance, availability,
  security, usability, data retention, scalability); UNKNOWN NFR → assumption + risk
- Step 6: Critical path and slack calculation (Steps 6A–6D); two new task fields:
  `critical_path` (boolean), `slack_days` (integer); critical path summary block
- Step 7: Added rule requiring risks to reference task IDs from Step 6

**What consolidated from archive:**
- v1.1.0 — SDLC, NFR, critical path (three reasoning additions)
- v1.1.1 — task reference rule in Step 7 (single rule addition)

**Rubric scores:** D3=3.8/5. Internal consistency dimension: 2→4/5.

---

## v1.2 — OUTPUT RELIABILITY
**File:** `prompts/v1.2_system.txt`
**Date:** March 2026
**Type:** FUNCTIONAL + STRUCTURAL — output structure and confidence calibration

**What changed from v1.1:**
- Confidence score calibration: mandatory deduction table (-5 per UNKNOWN constraint,
  -5 per assumption, -10 per CRITICAL risk, etc.) with hard caps:
  ≥5 assumptions → score ≤60; input quality LOW → score ≤45
- Viability Check (Step 8b): conditional gate when budget/deadline provided;
  NOT_VIABLE triggers 2–3 scoping options
- Complete JSON skeleton added to output contract — every field at correct nesting
  level with format constraints. Fixed 32 schema errors from v1.1 eval run.
- Explicit field format rules: enum values, ID string formats (A1, T1, R1),
  success_definition as List[str], RiskCategory uses "Integration" not "External"

**What consolidated from archive:**
- v1.2.0 — prompt caching enabled (infrastructure, no reasoning change)
- v1.3.0 — viability check Step 8b
- v1.4.0 — complete JSON skeleton in output contract
- v1.5.0 — explicit confidence deduction table with hard caps

**Rubric scores:** D1 failures: 32→0. D4 pass rate: 70%→90%.

---

## v1.3 — PRODUCTION ARCHITECTURE
**File:** `prompts/v1.3_system.txt`
**Date:** March 2026
**Type:** STRUCTURAL — output format change, latency reduction

**What changed from v1.2:**
- Prose report sections (Sections 1–9) removed from output contract entirely.
  Output is now: optional `<scratchpad>` (≤500 tokens) + single JSON block.
- Scratchpad instruction added: Claude works through critical path math, risk
  scoring, and confidence deductions in scratchpad before committing to JSON values.
- Confidence deduction table and open questions rules moved into output contract
  (applied in scratchpad, not written as prose output).
- effort_hours cap reinforced in format rules block: MAX 40.0, split if exceeded.
- user message (`_build_user_message`) updated to say JSON only — eliminates the
  contradiction where user message previously said "write prose sections first".
- `max_tokens`: 15000 → 8000 (JSON-only output fits in ~6,500 tokens).
- `GapType` enum: N_A → NA = "N/A" (fixes serialization ambiguity).
- Streaming token capture fixed: `chunk.delta.text` (not `chunk.text`);
  `message_start` / `message_delta` events captured for real cache metrics.
- Validator UNKNOWN defaults removed: missing enum fields now reported as schema
  errors rather than silently replaced with invalid values.

**What consolidated from archive:**
- v1.6.0 — JSON-only output, scratchpad instruction, max_tokens 8000
- v1.6.1 — effort_hours cap in format rules, JSON comment removed from skeleton

**Rubric scores:** D1=PASS. Latency: ~200s→~100s (cold cache). D3 unchanged.

---

## v1.4 — SCHEMA ALIGNMENT + HAIKU COMPATIBILITY
**File:** `prompts/v1.4_system.txt`
**Date:** March 2026
**Type:** Bug fix — schema mismatch + model compatibility

**What changed from v1.3:**
- Fixed `project_viability` output skeleton: exact field names only (`viability_status`,
  `gap_type`, `gap_amount`, `scoping_options`). Removed hallucinated fields
  (`budget_gap_amount`, `schedule_gap_weeks`, `gap_details`, `analysis`).
- Fixed `scoping_options` item key: `option_id` not `option`.
- Added null vs. non-null viability examples side-by-side in skeleton.
- Added `phases[n].percentage_of_total` minimum (5.0) to format rules.
- Added `Budget` to `RiskCategory` enum in `output_schema.py` (Haiku naturally
  produces this category; regenerated `output_schema.json`).
- `open_questions` capped at MAX 5 items in prompt (schema already had `max_length=5`).
- `open_questions.priority` constraint added: integer 1–5 only, NEVER exceed 5.
- Risk category list updated to include "Budget" in both the format rules and
  the reasoning process sections.

**Infrastructure changes:**
- Switched default model to `claude-haiku-4-5-20251001` for all development runs.
  Sonnet (`claude-sonnet-4-20250514`) reserved for final Demo Day baseline only.
- `max_tokens`: 8000 → 16000 (Haiku outputs are more verbose; 8k caused truncation).
- Workers default: 3 → 1 (Haiku free tier: 10k output tokens/min rate limit).
- Warmup call removed from `run_eval.py` (consumed token budget, no cache benefit).
- Rate-limit retry (3 attempts, 65s backoff) added to D1 and D4 eval helpers.

**Rubric scores (Haiku, 10 test cases):**
- D1 (Schema): PASS (10/10, 100%)
- D2 (Consistency): FAIL (variance=30.0, target <5) — Haiku confidence scoring is volatile
- D3 (Reasoning): PASS (4.75/5) — staffing_validity 3/5, all others 5/5
- D4 (Edge Cases): PASS (10/10, 100%)

---

## v1.5 — STRUCTURAL TRIM + ANTI-PATTERNS
**File:** `prompts/v1.5_system.txt`
**Date:** March 2026
**Type:** STRUCTURAL + FUNCTIONAL — prompt trim and input quality gates

**What changed from v1.4:**
- **Structural trim:** Removed SDLC/NFR definition prose. Trimmed phase milestones
  to 2 per phase. Removed critical path definition prose, kept calculation rules.
- Step 1 (EXTRACT): Added anti-pattern check — Solution Smuggling, Feature Factory,
  Stakeholder Driven. Flag any detected in open_questions (urgency "Before planning").
- Step 4 (ASSUMPTION LOG): Added `tradeoff` field — what plan gains vs. risks.
- Format rules: added `tradeoff` to assumption_log; restored open_questions MAX 5.
- Skeleton: `prompt_version` → v1.5.0.

**Builds on v1.4 (10 test cases):** D1 10/10, D2 FAIL, D3 4.75/5, D4 10/10.

**Rubric scores:** Pending eval.

---

## Versioning Rules (for future versions)

- **New minor version (v1.x):** new capability or reasoning addition with before/after
  eval scores showing measurable improvement. Requires a rubric run to justify.
- **New major version (v2.x):** breaking change to output structure or reasoning
  process (e.g., adding approval gate in Project 2).
- **Not a version:** whitespace, comment tweaks, one-line fixes, infrastructure
  changes with no eval impact. Use a descriptive git commit instead.
- Never overwrite an existing version file. Create a new file.
- Archive folder (`prompts/archive/`) is read-only — never edit archived files.
