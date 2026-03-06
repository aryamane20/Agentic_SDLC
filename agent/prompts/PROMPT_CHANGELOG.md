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

## v1.0.1 — Role / Knowledge Base Separation (Structural Refactor)
**Date:** March 2026
**Type:** STRUCTURAL — no reasoning changes, only file organisation
**Trigger:** Design decision to separate role (HOW to think) from knowledge base (WHAT to know)
so each can be iterated and evaluated independently.

**What changed:**
- Extracted `## KNOWLEDGE BASE` section from `system_prompt_v1.md` into 3 separate files:
  - `knowledge-base/templates/project-type-templates.md` — all 6 project type templates (expanded from 3)
  - `knowledge-base/risks/risk-patterns.md` — risk pattern catalog (significantly expanded)
  - `knowledge-base/staffing/role-definitions.md` — role benchmarks and effort estimates (expanded)
- `system_prompt_v1.md` now ends at BOUNDARIES section — pure role, no domain data
- `src/agent.py` updated with compiler pattern: `_build_system_context()` assembles role + KB at runtime
- Knowledge base files are more detailed than the original inline version

**What did NOT change:**
- 8-step reasoning process — identical
- Output contract — identical
- Boundaries — identical
- All test cases, schema, eval files — unchanged

**Why this matters for Project 3:**
- `_build_system_context()` in agent.py is the exact method that will be replaced with RAG retrieval
- The separation point is already clean — no refactoring needed when adding vector store

**Rubric impact:** Neutral (structural only). Re-run eval to confirm no regression.

---

## v1.1.0 — [NEXT VERSION — fill in after first eval run]
**Date:** TBD  
**Trigger:** [What eval result triggered this change?]  
**Changed:** [What specifically changed in the prompt?]  
**Rubric Before:** [scores]  
**Rubric After:** [scores]  
**Test Cases Affected:** [which TCs changed behavior?]

---

*Rule: Never overwrite a prompt version. Always create a new file (v2, v3...).*
*Rule: Always run eval before AND after a prompt change and record both scores.*
*Rule: If a change improves one test case but regresses another, document both.*
