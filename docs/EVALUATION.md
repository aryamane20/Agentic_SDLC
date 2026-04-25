# How we test PLANR (P2)

This document is for anyone who wants to know **what we test today**, **where files go**, and **how to run checks** — without digging through the whole repo.

**P3** (multi-agent pipeline, database sessions, RAG, etc.) is **out of scope** here. When this doc says “we,” it means the current P2 stack: FastAPI, file-based sessions, one PM agent, gates, refine, and the golden dataset.

---

## What lives under `outputs/`?

All **generated or saved run artifacts** go here (some paths are gitignored; see root `.gitignore`).

| Path | What it is | When it gets files |
|------|------------|---------------------|
| **`outputs/golden/`** | One JSON per golden case + `golden_replay.xlsx` from `run_golden.py` | Regenerate or replay the golden dataset |
| **`outputs/p1/eval/`** | P1 **scorecard JSON** from `scripts/run_eval.py` (live generate) | You run a full P1 eval with API calls |
| **`outputs/p2/e2e/`** | P2 **E2E JSON** from `scripts/run_p2_e2e.py` (real API) | You run scripted HITL E2E against a local server |
| **`outputs/{prompt_version}/`** | Cached P1 plan JSON per test case (replay source for `run_eval --replay`) | After `run_eval` generate; folder name matches prompt version |
| **`outputs/samples/`** | Committed reference snippets | Curated examples only |

### Golden dataset (lives under `outputs/`)

| Path | What it is |
|------|------------|
| `inputs/golden_dataset.json` | Defines **30 cases** (happy path, bad input, risk) and what each must satisfy. |
| `outputs/golden/{case_id}.json` | **One saved API response per case** (HTTP + body from `/reports/generate` or error JSON). Used to **replay** tests without calling the model again. |
| `outputs/golden/golden_replay.xlsx` | **Spreadsheet summary** produced by `run_golden.py --replay` — pass/fail per check. It is **not** a duplicate of the JSON files; it’s a **human-readable report** of the same replay. |

**Naming note:** The golden replay spreadsheet is `golden_replay.xlsx` (not `results.xlsx`).

---

## Three ways to run tests (cheat sheet)

| You want to… | Command | Uses API? |
|----------------|---------|-----------|
| Run all **P2** unit/API tests (gates, refine, mocks) | `make test-p2` or `make test-p2-baseline` | No |
| Run **input guard** only | `make test-input-guard` | No |
| Run **full** Python test suite | `make test` | No |
| **Score** saved golden JSON against `golden_dataset.json` | `make eval-replay-golden` | No |
| **Regenerate** golden files (costs tokens) | `make eval-generate-golden` | Yes |

Golden generate uses the prompt version set in `scripts/run_golden.py` (`GOLDEN_GENERATE_PROMPT_VERSION`) so runs stay aligned with the active system prompt.

---

## What the P2 tests actually cover

We group P2 checks into **layers** (cheap first):

1. **Gate on saved reports** — Does `evaluate_gate()` match what we expect on fixed JSON? Fast, no API.
2. **Refine replay** — Does the gate state evolve correctly across saved refine rounds? Fast, no API.
3. **API tests (mocked)** — Sessions, reports, gates, refine, uploads, 409 locking, etc. No real LLM.
4. **Live E2E (optional)** — Real API + real model; logs go under `outputs/p2/e2e/`. Manual / expensive.

Layers 1–3 are what `make test-p2` runs. Layer 4 is for demos or deep debugging.

---

## When does the approval gate fire?

The gate is a **safety net** before a PM treats a plan as “ready.” It turns on if **any** of these is true in the final report:

| Signal | Plain English |
|--------|----------------|
| Confidence **&lt; 60** | The plan is too shaky to rely on without a human look. |
| Any risk with **score `"CRITICAL"`** | Something could kill the project; PM must acknowledge. |
| **NOT_VIABLE** | The brief’s constraints don’t add up; we surface that instead of pretending. |
| **“Before planning”** open question | There is a blocker — *unless* the report already has a full enough work breakdown (see code in `approval_gate.py`). |

Refine and gate decisions are covered in `docs/ARCHITECTURE.md` and in the HITL skill.

---

## Intake guard (before the agent runs)

`POST /reports/generate` runs **`input_guard`** first. Bad or adversarial briefs get **422** with a structured error (e.g. `brief_missing`, `input_refused`). Good briefs go to the agent.

Tests: `make test-input-guard` and HTTP tests under `tests/p2/`.

---

## P1 eval vs P2

| | P1-style eval | P2 + golden |
|--|---------------|-------------|
| **Question** | Is the **agent’s plan quality** OK on classic TC-01…TC-10-style cases? | Do **API + gates + guard + saved outputs** behave as expected? |
| **Docs** | `docs/EVALUATION_RUBRIC.md`, `scripts/run_eval.py` | This file, `inputs/golden_dataset.json`, `scripts/run_golden.py` |
| **Outputs** | Scorecards under **`outputs/p1/eval/`**; cached plans under **`outputs/{prompt_version}/`** | **`outputs/golden/`** for the 30-case set |

Same product, different layers: rubric scoring is **not** the same thing as golden replay (they can both pass on different dimensions).

---

## Related docs

| File | Use it for |
|------|------------|
| `docs/EVALUATION_RUBRIC.md` | P1 quality dimensions and TC checks |
| `docs/ARCHITECTURE.md` | End-to-end design, API, gates |
| `inputs/test-cases-p2/README.md` | HITL scenario briefs (A / B / C) |
| `outputs/p2/e2e/README.md` | Where E2E JSON logs from `run_p2_e2e.py` go |

---

## P3 and later (not covered here)

Things like **database-backed sessions**, **multi-agent pipelines**, **LLM-as-judge** for Dimension 5, and **production load tests** are **not** part of the current P2 evaluation story. See `docs/ARCHITECTURE.md` for the roadmap; this doc stays focused on **what we run and store today**.
