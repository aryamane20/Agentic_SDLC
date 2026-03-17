# Pre_Mortem.md
## PM Digital Twin — Predicted Failure Modes
### Written: Before implementation begins (Session 2 deliverable)

---

## Premise

Imagine it is 4 weeks from now. The PM Digital Twin has been built and deployed.
It has failed. This document works backward from that failure to identify what caused it.

---

## Failure Mode Analysis

| # | Hypothesis | Trigger Condition | Detection Method | Severity | Mitigation |
|---|-----------|------------------|-----------------|----------|------------|
| F1 | Agent skips assumption log on clean inputs | Input appears complete, agent skips Step 4 | Schema validation — assumption_log is empty | HIGH | Schema validator enforces minItems: 1. Minimum assumption checklist in prompt |
| F2 | Sections are internally inconsistent | Risks don't reference tasks, staffing doesn't match phases | Rubric Dimension 3e (internal consistency) in run_eval.py | HIGH | Output contract requires cross-references. run_rubric_scoring checks coherence |
| F3 | Phase minimums violated under deadline pressure | TC-09 (tight timeline) — agent compresses Phase 4 below 15% | Business rule check in validator.py | HIGH | Hard rule in system prompt: "NEVER compress Phase 4 below 15%" |
| F4 | PM Confidence Score is overconfident | TC-05 (contradictory input) — agent scores itself 80+ | TC-05 expected max confidence of 40 | MEDIUM | Confidence deduction rules explicit in system prompt. TC-05 is edge case test |
| F5 | Hallucinated tasks for unknown project types | Input contains unfamiliar domain (biotech, legal) | Real PM comparison test | MEDIUM | Knowledge base templates cover 6 types. Unknown type → agent flags LOW confidence |
| F6 | JSON parsing fails | LLM adds prose before or after JSON block | parse_error flag in output + logger | LOW | Three-strategy extraction in main.py _extract_json. Fallback returns structured error |
| F7 | Generic risks not specific to input | Any run — risks sound copy-pasted | Rubric Dimension 3 (risk realism) | HIGH | Prompt requires risks to reference specific input details |
| F8 | Staffing plan missing QA role | Vague input doesn't mention testing | QA ratio business rule in validator | MEDIUM | Mandatory staffing heuristic: always include QA regardless of input |
| F9 | Over-allocation of roles | Single-person team inputs (TC-10) | Business rule: allocation_percent <= 80 | HIGH | Schema enforces maximum: 80. Validator flags violations |
| F10 | Contradictions not detected | TC-05 — impossible constraints accepted without comment | TC-05 must trigger CRITICAL risks + low confidence | MEDIUM | Contradiction detection in mandatory risk checklist |

---

## Most Likely Failure: F2 (Internal Inconsistency)

**Why this is most likely:**
The agent generates each section somewhat independently. Without explicit cross-referencing instructions, the risk register may identify risks that have no corresponding mitigation tasks in the project plan, and the staffing plan may not account for roles needed in high-risk phases.

**What we're doing about it:**
1. The output contract explicitly says "Risks must reference plan tasks via risk_flag"
2. The rubric internal_consistency scorer checks for cross-section coherence
3. TC-01 evaluation will specifically check whether a CRITICAL risk has a corresponding mitigation task in the plan

---

## Most Severe Failure: F3 (Phase Minimum Violation)

**Why this is most severe:**
A QA phase compressed below 15% in production means a PM would receive a plan that skips adequate testing — and might actually follow it. This is the scenario the course's "Would you deploy this on a Tuesday?" question is designed to catch.

**What we're doing about it:**
1. Hard rule in system prompt with explicit language: "NEVER compress below 15%"
2. Business rule validator flags this as a FAIL (not a warning)
3. TC-09 is specifically designed to trigger this — a 3-week timeline for a complex project

---

## Failure Modes Deliberately NOT Mitigated

| Failure | Why Not Mitigated |
|---------|------------------|
| Agent misunderstands highly technical domain | Out of scope for Project 1 — knowledge base covers standard software projects only |
| LLM API downtime | Infrastructure concern, not agent design concern |
| Input in non-English language | Out of scope for MVP |

---

*This pre-mortem was written before implementation. Compare to actual failures at Session 4 evaluation.*
