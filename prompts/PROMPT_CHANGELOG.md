# PROMPT_CHANGELOG.md
## System Prompt Version History

Track every significant change to the system prompt here.
Commit format: `prompt(vN): short description`

---

## v1.0.0 — Initial Implementation
**Date:** March 2026
**Files:** `system_prompt_v1.md`
**Rubric Scores:** [run eval to populate]

**What's in this version:**
- Full 8-step reasoning process (PMI/PMBOK grounded)
- Identity: Senior Internal Product PM, 8+ years
- All 5 system prompt components
- Inline knowledge base: Type A, C, D templates (later extracted — see v1.0.1)
- Risk pattern catalog (later extracted — see v1.0.1)
- Staffing benchmarks (later extracted — see v1.0.1)
- Hard output contract with JSON requirement

---

## v1.1.0 — Three Additions from Systems Analysis Course (Functional Change)
**Date:** March 2026
**Type:** FUNCTIONAL — reasoning and output structure both change
**Trigger:** Review of Satzinger et al. Systems Analysis & Design course material
revealed three gaps: missing SDLC approach recommendation (Ch.10),
missing non-functional requirements category (Ch.2), and missing
critical path / slack calculation (Ch.C PERT/CPM).

**What changed in system_prompt_v1.md:**

Step 2 — Added Part B: SDLC Approach
  - New definitions: Predictive, Adaptive, Hybrid SDLC with decision rules
  - Agent now outputs SDLC_APPROACH + APPROACH_RATIONALE after project type
  - Downstream: Adaptive/Hybrid triggers sprint structure in phases 2-3
    and adds Product Owner question to Section 7

Step 3 — Added Non-Functional Requirements category
  - New definitions: Functional vs Non-Functional requirements explained
  - Six new NFR fields: PERFORMANCE, AVAILABILITY, SECURITY, USABILITY,
    DATA_RETENTION, SCALABILITY
  - Rule: UNKNOWN NFR on user-facing system → assumption + risk (both required)

Step 6 — Added Critical Path and Slack Time
  - New definitions: critical path, slack time (float) — precise, not vague
  - Four-step calculation rule (6A-6D): build chains → find longest →
    mark critical → calculate slack for all others
  - Two new task fields: CRITICAL_PATH (boolean), SLACK_DAYS (integer)
  - New output block: CRITICAL PATH SUMMARY after task list
  - Rule connecting to Step 8: critical path tasks → full-time roles

**What changed in output_schema.json:**
  - report_metadata: added sdlc_approach (required), sdlc_rationale
  - assumption_log items: added source field (hard_constraint | soft_constraint | nfr | scope | other)
  - project_plan: added critical_path_summary (required top-level block)
  - task items: added critical_path (boolean, required), slack_days (integer ≥ 0, required)

**Rubric impact:** Expected improvement in:
  - Dimension 3 (reasoning quality) — Step 2 and Step 3 are now richer
  - Dimension 4 (edge cases) — NFR gaps now surface as explicit risks
  Re-run all 10 test cases and update scores below.

**Rubric scores:** [run eval to populate]

---

## v1.1.1 — Schema Compliance Fixes
**Date:** March 2026
**Type:** STRUCTURAL — format compliance, no reasoning changes
**Trigger:** First eval run showed field name mismatches and schema violations

**What changed in system_prompt_v1.md:**
- Added "CRITICAL: OUTPUT FIELD NAME REQUIREMENTS" section
- Explicit field names: pm_confidence_score (object), project_type, assumption_log, risk_register
- project_plan structure: added critical_path_summary, task structure details
- staffing_plan: skills_required as array (not string)
- assumption_log: source enum values (hard_constraint/soft_constraint/nfr/scope/other)
- Phase percentage constraints: Phase 1 >=10%, Phase 4 >=15%
- Task effort_hours: MAX 40 (split larger tasks)

**What changed in src/validator.py:**
- Added _normalize_field_names() to handle field variations
- Maps: classification->project_type, assumptions->assumption_log, risks->risk_register
- Sets defaults for missing metadata fields

**Rubric impact:** Significant improvement in Dimension 1 (schema validation)
Test Cases Affected: All (previously failing schema validation)

---

## v1.2.0 — [RESERVED FOR NEXT PROMPT CHANGE]
**Date:** TBD  
**Trigger:** [What eval result triggered this change?]  
**Changed:** [What specifically changed in the prompt?]  
**Rubric Before:** [scores]  
**Rubric After:** [scores]  
**Test Cases Affected:** [which TCs changed behavior?]

---

## v1.2.0 — Performance: Prompt Caching Enabled
**Date:** March 2026
**Type:** PERFORMANCE — no reasoning changes, infrastructure optimization
**Trigger:** Need to reduce API costs and latency for eval runs

**What changed in agent/main.py:**
- System prompt now passed as list with cache_control for Claude 4 prompt caching
- New format: `system=[{"type": "text", "text": <prompt>, "cache_control": {"type": "ephemeral"}}]`
- Response now captures cache metrics: `cache_read_input_tokens`, `cache_creation_input_tokens`
- Logging updated to show cache status (cache_read vs cache_created)

**How caching works:**
- First API call: `cache_creation_input_tokens` = full prompt size, `cache_read_input_tokens` = 0
- Subsequent calls (within 5 minutes): `cache_read_input_tokens` = full prompt size, `cache_creation_input_tokens` = 0
- Cache TTL: 5 minutes — expires between separate sessions, holds for entire eval suite

**What changed in scripts/run_eval.py:**
- Added warmup call before test case loop to prime the cache
- Without warmup: TC-01 pays full price, inflating latency numbers
- With warmup: All 10 test cases benefit from cached prompt equally

**Cost impact (expected):**
- Eval run without cache: 10 × full prompt tokens
- Eval run with cache: 1 × full prompt tokens + 9 × cached reads
- Savings: ~90% on prompt token costs for eval runs

**Latency impact (expected):**
- First call: Same latency as before (prompt processing time)
- Subsequent calls: Significantly faster (no reprocessing of system prompt)

**Rubric impact:** None — this is purely infrastructure, no reasoning changes

---

## v1.3.0 — Conditional Viability Check (Functional Change)
**Date:** March 2026
**Type:** FUNCTIONAL — new reasoning step and output section added
**Trigger:** Need to flag projects that exceed budget or timeline constraints with scoping options

**What changed in prompts/v1.3.0_system.txt:**
- Added Step 8b: VIABILITY CHECK (Conditional)
  - Only runs if budget OR deadline is provided in input
  - Budget check: NOT_VIABLE if estimated_cost > budget × 1.5
  - Schedule check: NOT_VIABLE if duration > deadline × 1.3, AT_RISK if > 1.0
  - Generates 2-3 scoping options when status is NOT_VIABLE

- Added Section 9: PROJECT VIABILITY FLAG to output contract
  - VIABILITY_STATUS: VIABLE | AT_RISK | NOT_VIABLE | CANNOT_ASSESS
  - GAP_TYPE: BUDGET | SCHEDULE | BOTH | N/A
  - GAP_AMOUNT: specific gap or "N/A"
  - SCOPING_OPTIONS: only if NOT_VIABLE

**What changed in schemas/output_schema.py:**
- Added ViabilityStatus enum
- Added GapType enum
- Added ScopingOption model
- Added ProjectViability model
- Added optional project_viability field to PMReport

**What changed in agent/viability_checker.py (NEW):**
- Created new module with conditional logic
- _extract_constraints(): parses budget/deadline from raw input
- check_viability(): applies thresholds, generates scoping options

**What changed in agent/runner.py:**
- Added check_viability_flag parameter to run_with_validation()
- Integrates viability check after agent completes
- Adds project_viability to report when constraints provided

**What changed in agent/validator.py:**
- Added viability validation rules
- Validates status values and scoping_options when NOT_VIABLE

**Rubric impact:** New Dimension 4 assertions:
- TC-05: viability_status=NOT_VIABLE, gap_type=BOTH, scoping_options>=2
- TC-09: viability_status=NOT_VIABLE, gap_type=SCHEDULE, scoping_options>=2
- TC-04: project_viability should be None (no constraints)

**Authoritative Viability Determination:**
- Section 9 (PROJECT VIABILITY FLAG) in the LLM output is **narrative reasoning only** — it explains the agent's own analysis of viability
- The authoritative, deterministic viability assessment comes from **viability_checker.py post-processing module**
- This module extracts constraints from input, calculates estimated cost from staffing plan, applies thresholds programmatically
- The post-processed viability is what triggers approval gates in production; Section 9 is supporting context for the PM

---

*Rule: Never overwrite a prompt version. Always create a new file (v2, v3...).*
*Rule: Always run eval before AND after a prompt change and record both scores.*
*Rule: If a change improves one test case but regresses another, document both.*
