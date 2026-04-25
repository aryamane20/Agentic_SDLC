# EVALUATION.md — Project 2 (HITL / Gates / Refinement)

This doc explains how we test the P2 features — the approval gate, the refine loop, and the API that connects the frontend to the agent. It covers what we test, how to run the tests, and what we've deliberately left for P3.

**Related docs**

| Doc | What it's for |
|-----|---------------|
| `docs/EVALUATION_RUBRIC.md` | P1 quality checks (schema, consistency, PM output scoring) |
| `docs/ARCHITECTURE.md` | Full system design — API, gates, sessions |
| `inputs/test-cases-p2/README.md` | The 3 test scenarios with briefs and expected behavior |
| `results/p2/e2e/README.md` | Where live E2E logs are saved |

**P1 vs P2 — what each phase tests**

| Phase | The question it answers | How |
|-------|------------------------|-----|
| **P1** | Is the agent's output good quality? | Eval scripts + rubric scoring |
| **P2** | Does the gate / refine / API machinery work correctly? | Pytest on fixtures + mocked API tests + optional live run |

---

## The 4 Test Layers

We test P2 in four layers, from cheapest to most expensive:

| Layer | What it checks | Automated? | Costs tokens? |
|-------|----------------|------------|---------------|
| **D1 — Gate on frozen JSON** | Does the gate fire correctly on pre-saved reports? | ✅ Yes | No |
| **D2 — Refinement replay** | Does the gate behave correctly across a multi-round refine sequence? | ✅ Yes | No |
| **D3 — Full API tests** | Do all the API endpoints work correctly end-to-end? | ✅ Yes | No |
| **D4 — Live run with real LLM** | Does the whole thing work with a real agent and real API calls? | 🔶 Manual only | Yes |

**D1–D3 pass criteria:** Run `make test-p2-baseline` — all tests must be green with no real API calls made.

**D4 pass criteria:** Subjective review — gate reasons should match what's in the report; logs saved under `results/p2/e2e/`.

---

## What Triggers the Gate

The gate fires whenever **any one** of these conditions is true in the agent's output. It collects **all** matching reasons before deciding — so if two or more conditions are true at once, the PM sees all of them.

| Condition | When it fires | Why it matters |
|-----------|---------------|----------------|
| **Confidence score below 60** | The agent's `pm_confidence_score` is less than 60 | Plan quality is too low to act on without a human review |
| **CRITICAL risk in the register** | Any risk in `risk_register[]` has `score == "CRITICAL"` | Forces the PM to consciously acknowledge an existential risk before proceeding. Every matching CRITICAL risk is collected — the gate doesn't stop at the first one. |
| **Project marked NOT_VIABLE** | `project_viability.viability_status == "NOT_VIABLE"` | The constraints are impossible as stated — this can't be silently passed through |
| **Unanswered "Before planning" question** | Any `open_questions[]` has `urgency == "Before planning"` AND the plan doesn't already have a full WBS (≥5 phases, at least 1 task) | There's a blocking question that needs answering before the team can start — unless a real plan already exists, in which case the question is probably already resolved |

**What the gate does NOT do:** It doesn't look at validation errors, Langfuse logs, or raw LLM text. It only reads the final report fields listed above.

**Approving or rejecting:** The PM records their decision via `POST /gates/{report_id}/decision`. This logs the decision but doesn't recheck the triggers — it's a human sign-off, not a re-run.

---

## The 3 Test Scenarios

| Scenario | Brief style | What it's testing |
|----------|------------|-------------------|
| **A — Happy path** | Detailed, well-defined | Gate should stay clear. Tests the "no alert needed" path. |
| **B — Low confidence** | Vague — no deadline, no budget, no team | Gate should fire on confidence. Tests the refine loop under sustained review pressure. |
| **C — Critical risk + NOT_VIABLE** | PHI data, public deadline, 3-person team, unfinished EPIC connector | Gate should fire hard (all 3 conditions). Tests whether the agent correctly flags an impossible project — and whether refinements can honestly reduce risk. |

Each scenario has a `brief.txt`, a `manifest.json` for scripted runs, and optional `e2e_feedback/round_*.json` files with realistic PM feedback to replay.

---

## D1 — Gate on Frozen JSON

**What it does:** Runs `evaluate_gate()` against pre-saved JSON files and checks whether the gate fires as expected.

**Why frozen files:** They're fast, deterministic, and don't cost tokens. When gate logic changes, these catch regressions immediately.

```bash
pytest tests/p2/test_p2_gates_fixtures.py -v
```

---

## D2 — Refinement Replay

**What it does:** Checks the gate state across a multi-round refinement sequence — initial plan, after round 1, after round 2 — using pre-saved snapshots.

**Why snapshots:** Tests whether the gate correctly clears or stays fired as the plan evolves, without needing to replay the LLM.

```bash
pytest tests/p2/test_p2_refinement_replay.py -v
```

---

## D3 — Full API Tests (Mocked)

**What it covers:** Every major API endpoint and user-facing behavior:

- All GET endpoints (`/reports/{id}`, `/gates/{id}`, `/sessions`, `/sessions/{id}`)
- User isolation — User A cannot see User B's sessions or reports
- Document upload (`.txt`, `.md`, `.pdf`, `.docx`, oversized, empty, wrong type)
- Validation retry — agent returns bad JSON twice, then valid; confirms 3-attempt loop works
- Refine allowed even when gate is fired (gate is a warning, not a lock)
- 409 returned when `expected_revision` is stale (optimistic locking)
- 409 does not write to disk (session not mutated on conflict)

**The Anthropic client and disk store are both mocked** — no tokens, no file I/O.

```bash
pytest tests/p2/ -v
```

Or just:

```bash
make test-p2-baseline
```

---

## D4 — Live E2E (Real LLM)

**What it does:** Runs the full workflow against a real running API — generate, refine, gate evaluation, all with the actual Anthropic model.

**Prerequisites:**
1. Dependencies installed (`requirements.txt` + `backend/requirements.txt`)
2. `ANTHROPIC_API_KEY` set in `.env`
3. API running: `uvicorn backend.api.main:app --reload --port 8000`

```bash
# Run a specific scenario
python scripts/run_p2_e2e.py --scenario scenario-a-happy-path --mode manifest
python scripts/run_p2_e2e.py --scenario scenario-b-low-confidence --mode file
python scripts/run_p2_e2e.py --scenario scenario-c-critical-risk --mode interactive
```

**Outputs:** Saved to `results/p2/e2e/*.json`.

---

## What's Mocked vs What's Real

| Component | D1–D3 (pytest) | D4 (live E2E) |
|-----------|----------------|---------------|
| Gate logic | Real | Real |
| Schema validation on generate | Not tested in P2 pytest | Real |
| PMAgent / Anthropic calls | Mocked | Real |
| Session file store | Mocked or temp dir | Real files on disk |

---

## When to Run What

| Situation | What to run |
|-----------|-------------|
| You changed `approval_gate.py` | `pytest tests/p2/ -v` |
| You changed a refine or reports router | `pytest tests/p2/ -v` |
| Before a demo or release | D1–D3 + one D4 scenario on `manifest` mode |
| After a prompt change that affects HITL | D4 scenarios A and B |

---

## What This Protects Against

| Risk | How PLANR handles it | Where tested |
|------|----------------------|--------------|
| Impossible inputs (contradictory constraints) | Returns `NOT_VIABLE` with scoping options instead of a confident bad plan | `EVALUATION_RUBRIC.md` D4 |
| Impossible timeline | Flags CRITICAL/HIGH schedule risk + `NOT_VIABLE` | `EVALUATION_RUBRIC.md` D4 |
| Understaffed project | Detects staffing gap + `NOT_VIABLE` | `EVALUATION_RUBRIC.md` D4 |
| Vague brief | Lowers confidence ≤50 + surfaces ≥5 assumptions | `EVALUATION_RUBRIC.md` D4 |
| Low-confidence plan reaching action | Gate fires at confidence < 60 and holds for PM review | Gate trigger conditions above |
| CRITICAL risk being silently approved | Gate fires on any CRITICAL risk — all matching risks are collected and shown | Gate trigger conditions above |
| Viable-looking but impossible project | Gate fires on `NOT_VIABLE` | Gate trigger conditions above |
| Inconsistent outputs across runs | Same brief run 5× must have confidence variance < 15; type and SDLC must be identical | `EVALUATION_RUBRIC.md` D2 |

---

## Known Gaps (Deliberately Left for P3)

These are not oversights — they're explicit decisions to keep P2 focused. P3 owns these.

| Gap | What it means | Planned for |
|-----|---------------|-------------|
| **Multi-writer file race** | Two tabs refining the same session simultaneously could corrupt the JSON file. The `expected_revision` / 409 flow protects stale *reads*, but not concurrent *writes* at the file level. | P3 (needs a database) |
| **No full lifecycle test without mocks** | No single pytest runs generate → gate → refine → approve → re-fetch against a live API. D4 is the manual substitute. | P3 |
| **Gate reasons not golden-tested** | D1/D2 check whether `fired` is true or false, but don't assert the exact reason strings against a ground truth. | P3 if needed |
| **No performance testing** | Gate and validation latency under load has never been measured. | P3 |
| **P1 rubric Dimension 5** | Still manual — no LLM-as-judge in P2. | P3 |
| **Prompt injection** | A brief containing "ignore your system prompt" — no test exists. | P3 intake layer |
| **Compliance bypass** | A brief that quietly asks to skip legal/security steps — untested. | P3 intake layer |
| **$0 or negative budget** | Agent behavior on malformed financial inputs is not tested. | P3 |
| **Very long briefs** | Quality at 5,000+ word inputs not measured. | P3 |
| **PII in brief** | No handling or redaction test for employee names, salaries in input. | P3 enterprise track |

---

## Why the Gate Is the Key Safety Net

The approval gate is P2's main protection against a bad plan reaching execution. A PM cannot act on budget or staffing recommendations without either the gate clearing naturally, or the PM explicitly choosing to override it. Every override is logged append-only in `logs/gate_decisions.jsonl`. This means there's always an audit trail when a human chose to proceed despite a CRITICAL risk or a confidence score below 60.

---

## One-Command Regression Check

```bash
make test-p2-baseline
```

Which runs:

```bash
pytest tests/p2/ -v
```

*Aligned with gate implementation in `backend/api/services/approval_gate.py` and E2E scripts under `scripts/run_p2_e2e.py`.*
