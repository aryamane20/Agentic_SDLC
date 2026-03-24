# Evaluation_Rubric.md
## PM Digital Twin — Full Evaluation Framework

---

## Overview: 5 Evaluation Dimensions

| Dimension | What It Tests | Automated? | Target |
|-----------|--------------|------------|--------|
| 1. Schema Validation | Output structure correctness | ✅ Fully | 100% pass rate |
| 2. Consistency | Same input → same output (3 runs, TC-01) | ✅ Fully | Variance < 15, same 10-pt band, type + SDLC match |
| 3. Reasoning Quality | PM thinking quality (rubric) | 🔶 Semi | Average > 3.5/5 |
| 4. Edge Case Handling | Behavior on difficult inputs | ✅ Mostly | > 80% pass rate |
| 5. PM Comparison | Agent vs real PM output | ❌ Manual | No embarrassment test |

---

## Dimension 1: Schema Validation

**What it checks:** Does the output contain all required fields in the correct format?

**How to run:**
```bash
python scripts/run_eval.py --dimension schema
```

**Pass criteria:** Every field in `output_schema.json` is present and correctly typed.

**Business rules also checked (beyond JSON schema):**
- Phase count is exactly 5
- Phase 1 ≥ 10% of timeline
- Phase 4 ≥ 15% of timeline
- No role allocated > 80%
- QA hours ≥ 25% of dev hours
- Risk register has ≥ 3 entries
- Assumption log has ≥ 1 entry
- PM Confidence Score is 0-100
- Open questions ≤ 5

---

## Dimension 2: Consistency

**What it checks:** Does the same input produce consistent output across **3** runs (TC-01)?

**How to run:**
```bash
python scripts/run_eval.py --dimension consistency
```

**Pass criteria:**
- PM Confidence Score variance < 15 points, all scores within same 10-point band, across 3 runs (TC-01)
- Project type and SDLC approach identical across all runs

**Why this matters:** Production agents must be predictable. A PM that gives wildly different assessments of the same project on different days is not trustworthy.

---

## Dimension 3: Reasoning Quality Rubric

**What it checks:** Does the agent actually think like a PM, or does it just fill a template?

**How to run:**
```bash
python scripts/run_eval.py --dimension rubric
```

**Scoring guide (1-5 per sub-dimension):**

### 3a: Assumption Quality
| Score | Description |
|-------|-------------|
| 5 | Every assumption has PMI basis + specific consequence. Assumptions are non-obvious gaps. |
| 4 | Most assumptions have PMI basis. Consequences are specific. |
| 3 | Assumptions present but PMI basis is vague. Consequences are generic. |
| 2 | Some assumptions logged but incomplete format. |
| 1 | Assumption log missing or trivially filled. |

### 3b: Plan Completeness
| Score | Description |
|-------|-------------|
| 5 | All 5 phases present. Percentages correct. No phase below minimum. Tasks are specific and assignable. |
| 4 | All 5 phases, minor percentage deviation. Tasks are specific. |
| 3 | All 5 phases present but allocations off. Tasks are somewhat vague. |
| 2 | Missing a phase or phases compressed below minimums. |
| 1 | Plan is skeletal, phases missing, tasks too vague to assign. |

### 3c: Risk Realism
| Score | Description |
|-------|-------------|
| 5 | Risks are specific to the input. Mandatory checklist items all present. 3+ categories represented. |
| 4 | Risks mostly specific. Most mandatory items present. |
| 3 | Risks present but could apply to any project. |
| 2 | Generic risk list. Missing obvious risks from mandatory checklist. |
| 1 | Fewer than 3 risks. Missing trigger/mitigation/contingency. |

### 3d: Staffing Validity
| Score | Description |
|-------|-------------|
| 5 | No over-allocation. QA ≥ 25% dev. PM included. Skills are specific. Critical path identified. |
| 4 | No over-allocation. Most PMI rules followed. |
| 3 | Minor violations. Skills are somewhat generic. |
| 2 | Over-allocation present or QA missing. |
| 1 | Staffing plan doesn't match the project plan phases/tasks. |

### 3e: Internal Consistency
| Score | Description |
|-------|-------------|
| 5 | CRITICAL risks have mitigation tasks in the plan. Staffing matches phase involvement. Open questions reflect actual gaps. |
| 4 | Most cross-section references are coherent. |
| 3 | Sections mostly standalone. Minor cross-references. |
| 2 | Obvious disconnects between sections. |
| 1 | Sections clearly generated independently. No coherence. |

---

## Dimension 4: Edge Case Handling

**Test case expectations:**

| Test Case | Input Quality | Expected Behavior |
|-----------|--------------|------------------|
| TC-01 | Perfect | Confidence ≥ 55. Assumptions ≤ 7. TYPE_A. SDLC present. Critical path present. |
| TC-02 | Good | Schema valid. No specific confidence/assumption checks. |
| TC-03 | Medium | Schema valid. No specific confidence/assumption checks. |
| TC-04 | Vague (1 sentence) | Confidence ≤ 50. Assumptions ≥ 5. At least 1 risk. Viability = null. |
| TC-05 | Contradictory | Confidence ≤ 40. Contradiction detected (structural: confidence ≤ 20 + NOT_VIABLE + BOTH). Viability = NOT_VIABLE, gap = BOTH, ≥ 2 scoping options. |
| TC-06 | Type A project | Classified as TYPE_A. |
| TC-07 | Type C project | Classified as TYPE_C. |
| TC-08 | Type D project | Classified as TYPE_D. |
| TC-09 | Impossible timeline | At least 1 timeline/schedule/deadline risk flagged. CRITICAL or HIGH risk present. Viability = NOT_VIABLE, gap = SCHEDULE or BOTH, ≥ 2 scoping options. |
| TC-10 | Solo team, large project | Confidence ≤ 50. Staffing gap detected (structural: NOT_VIABLE + BOTH + risk_count ≥ 8). Viability = NOT_VIABLE, gap = BOTH, ≥ 2 scoping options. |

**Note on structural checks (TC-05, TC-10):** The evaluator uses structural outcome signals rather than keyword matching. A contradiction is confirmed by `confidence ≤ 20 AND NOT_VIABLE AND gap = BOTH` — not by scanning for the word "contradict". A staffing gap is confirmed by `NOT_VIABLE AND gap ∈ {BOTH, BUDGET} AND risk_count ≥ 8`.

---

## Dimension 5: Real PM Comparison (Manual)

**How to run this:**
1. Use TC-01 (perfect input — employee onboarding portal)
2. Open `outputs/v1.6.1/tc-01-perfect.json`
3. Independently produce what a good PM would create:
   - A rough project plan (phases, key milestones)
   - Top 5 risks
   - Team structure needed
4. Compare agent output to your manual output

**Scoring question:** "Would a senior PM be embarrassed to sign off on this output?"
- **Pass:** No — output is reasonable, well-structured, assumptions are sound
- **Fail:** Yes — output has obvious gaps, unrealistic timelines, missing critical risks

**What to look for specifically:**
- Does the agent catch the Workday API integration risk? (TC-01 has an external dependency)
- Does the agent flag SOC 2 as a compliance constraint affecting timeline?
- Does the agent recommend a UX designer for Phase 1 given the portal scope?
- Is the timeline realistic for a 4-person team with a June 30 deadline?

---

### Future: Dimension 5 for Project 3 (LLM-as-Judge)

> **Note:** Dimension 5 is currently **purely manual** — this is intentional for Project 1. However, for **Project 3** (multi-agent orchestration at scale), manual comparison becomes a bottleneck.

**Project 3 pipeline adds two new eval concerns:**

**1. Use Case Quality** — does the Use Case Agent produce correct, complete artifacts?
- Actor identification coverage (all human + external system actors named)
- Use case naming and granularity (each UC = one goal one actor can achieve)
- Relationship correctness (includes/extends semantically accurate)
- draw.io XML validity — does it parse and render without errors in Kroki?
- Traceability — do downstream agents reference UC IDs in their output?

**2. Diagram rendering** — does the two-step pipeline produce usable diagrams?
- LLM produces valid structured JSON (actors, use_cases, relationships fields present)
- `drawio_generator.py` produces parseable XML with no overlapping elements
- Kroki API returns a PNG (200 status, non-empty image)
- .drawio file opens correctly in `app.diagrams.net`

**Recommended approach for Project 3:**
- Implement **LLM-as-judge** — a second Claude call scoring agent output against a rubric
- Judge compares: use case completeness, plan-to-UC traceability, risk-to-UC traceability, staffing-to-UC traceability, synthesis coherence
- Outputs a score + justification (same 1-5 scale as Dimension 3)
- Add **D6: Diagram Quality** — automated: XML parses + Kroki renders + traceability IDs present

**Why this matters in "Delegating" mode:**
- Multi-agent systems produce more varied outputs
- Human review becomes time-prohibitive at scale
- LLM-as-judge provides consistent, fast feedback for iteration
- Diagram rendering is fully automatable — no human needed

This pattern — using an LLM to evaluate another LLM's output — is the natural evolution from the semi-automated rubric in Dimension 3.

---

## Evaluation Cadence

| When | What to Run | Why |
|------|-------------|-----|
| After every prompt version change | Dimensions 1 + 3 on TC-01 | Quick feedback loop |
| After build session (Session 3) | All dimensions | Full baseline |
| Before Session 4 demo | All dimensions | Final evaluation |
| When adding test cases | Dimension 4 only | Regression check |

---

## Tracking Rubric Scores Over Prompt Versions

| Prompt Version | D1 Schema | D2 Consistency | D3 Rubric Avg | D4 Edge Cases | D5 PM compare | Notes |
|----------------|-----------|----------------|---------------|---------------|---------------|-------|
| v1.4 | 10/10 | FAIL (variance 30) | 4.75/5 (staffing 3/5) | 10/10 | — | Haiku, temp 0.3 |
| v1.5 | 10/10 | FAIL (variance 52) | Pending | 10/10 | — | Structural trim + anti-patterns. Variance worse — mechanical rule alone insufficient. |
| v1.6 | 10/10 | FAIL (variance 25) | Pending | Pending | — | SDLC tiebreaker, staffing completeness rule, temp 0.0. D2 target not met. |
| **v1.6.1** | **10/10** | **PASS** (variance **0.0**; TYPE_A ×3, Predictive ×3) | **5.0/5** | **10/10** | **PENDING** | NFR materiality gate: TC-01 **3 assumptions**, score **82** live. Full suite `--generate` + `--all --replay` 2026-03-21. D2 also verified on TC-04 (variance=0.0) and TC-05 (variance=0.0). D1 warnings only on TC-05 (94% alloc) and TC-10 (100% alloc) — both are stress test cases, not agent failures. **Complete D5** using `outputs/v1.6.1/tc-01-perfect.json`. |

**D2 pass criterion (v1.6.1 and forward):** variance < 15 AND all scores within same 10-point band AND type consistent AND SDLC consistent. Variance = 0.0 on v1.6.1 also satisfies the stricter original target of < 5.

*Active version: **v1.6.1**. D5: compare agent TC-01 output to your own plan — document PASS/FAIL in the D5 column above.*