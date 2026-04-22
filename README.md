
# PLANR — Project 1
### Course: Vibe Coding to Agent Engineering (Spring 2026)
### Student: Arya Mane | Role: Developer/PM

---

## What This Is

**PLANR** is the product name: short, readable, works as a verb (“Let me Planr this first”). Under the hood it is an AI agent that replicates the thinking process of a senior **Internal Product Project Manager**. Given any project requirements — vague or detailed — the agent runs an 8-step reasoning process grounded in PMI/PMBOK frameworks and produces an integrated output: project plan, risk register, and staffing plan.

This is **not** a form-filling tool. The agent is designed to think first, then produce — the same way a real PM does.

---

## Course Project Progression

This use case evolves across all three course projects:

| Project | Mode | What Changes |
|---------|------|-------------|
| **Project 1** (done) | Doing | Single agent, embedded knowledge, deterministic output |
| **Project 2** (done) | In progress | FastAPI HITL backend + React/Vite frontend + approval gates + refinement loop — fully implemented, tested (100 tests), and smoke-tested across all 3 scenarios |
| **Project 3** | Delegating | Multi-agent pipeline: **Use Case Agent** (actors, use cases, **draw.io + Kroki PNG**) → Intake → Planning → Risk → Staffing → **Synthesis**; RAG per agent; final report = BA + PM output, cross-grounded (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §7) |

---

## Repository Structure

```
Agentic_SDLC/
│
├── README.md                        ← Architecture answers + project status
├── .gitignore                      ← Standard Python + logs exclusion
├── requirements.txt                ← All Python dependencies pinned
│
├── agent/                          ← Agent implementation code
│   ├── __init__.py
│   ├── main.py                     ← Entry point: runs the agent end-to-end
│   ├── runner.py                   ← run_with_retry(), run_with_validation()
│   ├── logger.py                   ← Structured run logger (writes to logs/)
│   ├── validator.py                ← Output schema validation using pydantic
│   └── viability_checker.py        ← Project viability assessment logic
│
├── prompts/                        ← Versioned prompt files (immutable once committed)
│   ├── README.md                   ← Prompt design decisions and version changelog
│   ├── PROMPT_CHANGELOG.md        ← Full version history
│   ├── v1.0_system.txt           ← Baseline prompt
│   ├── v1.1_system.txt           ← Reasoning completeness (SDLC, NFR, critical path)
│   ├── v1.2_system.txt           ← Output reliability (JSON skeleton, calibration)
│   ├── v1.3_system.txt           ← Production architecture (JSON-only, scratchpad)
│   ├── v1.4_system.txt           ← Haiku compatibility (Budget risk, priority caps)
│   ├── v1.5_system.txt           ← Structural trim + anti-patterns
│   ├── v1.6_system.txt           ← D2/D3/D1 fixes, SDLC tie-breaker, hard caps
│   ├── v1.6.2_system.txt         ← active default in code (v1.6.1 retained for replay)
│   └── archive/                   ← Intermediate prompt versions for reproducibility
│
├── schemas/                        ← Input/output schema definitions
│   ├── input_schema.py            ← Pydantic model for expected input
│   ├── output_schema.py           ← Pydantic model for expected output
│   └── output_schema.json         ← Generated JSON schema (from Pydantic)
│
├── tests/                          ← pytest test suite
│   ├── __init__.py
│   ├── conftest.py                ← pytest fixtures
│   ├── p2/                        ← P2: pytest only; data under inputs/test-cases-p2/fixtures/
│   ├── test_happy_path.py         ← Valid input → expected output
│   ├── test_edge_cases.py         ← Malformed/empty/boundary inputs
│   └── test_retry.py              ← Mock API failure → retry → success
│
├── logs/                           ← Run logs (gitignored except samples)
│   ├── .gitignore                 ← Ignore all run logs EXCEPT samples/
│   └── samples/
│       ├── sample_success.json     ← Representative successful run
│       └── sample_failure.json     ← Representative failure run
│
├── docs/                           ← Architecture doc, pre-mortem, design decisions
│   ├── ARCHITECTURE.md            ← Full system design (P1–P3)
│   ├── PRE_MORTEM.md              ← Failure mode table (predicted + discovered)
│   ├── EVALUATION_RUBRIC.md       ← P1 eval dimensions and rubric scoring
│   ├── EVALUATION.md              ← P2 test layers, gate conditions, how to run
│   └── DEMO.md                    ← Pre-demo checklist + scenario briefs
│
├── scripts/                        ← Utility scripts
│   ├── run_eval.py                ← Runs agent on eval set; scorecard → results/p1/eval/
│   └── analyze_logs.py            ← Parses logs/ for latency, failure rate
│
├── frontend/                      ← Project 2: Vite + React + Tailwind + shadcn-style UI
│   ├── README.md                  ← `npm run dev` (proxies API on :8000)
│   └── src/components/ui/        ← Registry components (e.g. particle-text-effect)
│
├── backend/                       ← Project 2: backend root (deps, future shared code)
│   ├── requirements.txt           ← fastapi, uvicorn (install with root requirements.txt)
│   └── api/                       ← FastAPI app package
│       ├── main.py                ← App + CORS + routers
│       ├── routers/               ← sessions, reports, gates, refine
│       ├── services/              ← approval_gate, feedback_logger, refinement
│       ├── models/                ← Pydantic API models
│       └── db/store.py            ← JSON persistence under sessions/
│
├── knowledge-base/                 ← PM domain knowledge (inline for P1)
│   ├── templates/
│   │   └── project-type-templates.md ← All project type templates (A-F)
│   ├── risks/
│   │   └── risk-patterns.md      ← PMI-grounded risk catalog
│   └── staffing/
│       └── role-definitions.md    ← Role benchmarks and effort estimates
│
├── inputs/                         ← All test-case inputs (P1 + P2)
│   ├── test-cases-p1/             ← P1: tc-01 … tc-10 (.txt briefs for run_eval)
│   ├── test-cases-p2/             ← P2: scenario-*/brief.txt + manifest.json
│   │   └── fixtures/              ← P2: gates/*.json + refinement/*/ (frozen reports for pytest)
│   └── test-cases -> test-cases-p1 ← Symlink for legacy paths
│
├── results/                        ← Eval scorecards & run logs (committed samples optional)
│   ├── p1/eval/                   ← run_eval.py JSON scorecards (was eval/results/)
│   ├── p1/README.md
│   └── p2/e2e/                    ← P2 manual / scripted workflow logs
│
└── outputs/                       ← Auto-generated, gitignored except samples
    └── samples/
        └── tc-01-sample_output.json ← Reference output for TC-01
```

---

## How to Run

### Setup
```bash
git clone <your-repo>
cd Agentic_SDLC
pip install -r requirements.txt
pip install -r backend/requirements.txt
# Add your API key to .env (ANTHROPIC_API_KEY)
```

### Project 2 — Run the FastAPI backend (from repo root)
```bash
uvicorn backend.api.main:app --reload --port 8000
```
Open **http://127.0.0.1:8000/docs** for OpenAPI. Typical flow: `POST /sessions` → `POST /reports/generate` with `session_id` + `brief` → optional `POST /gates/{report_id}/decision` → optional `POST /reports/{report_id}/refine`. Responses include `report_revision`; refine and gate decision accept optional `expected_revision` — if it does not match the server, the call returns **409** (`report_revision_conflict`) so stale tabs do not silently overwrite. Session JSON lives in `sessions/` (gitignored). Gate decisions append to `logs/gate_decisions.jsonl`.

**P2 scripted E2E** (uses the same API + agent; logs under `results/p2/e2e/`):

```bash
python scripts/run_p2_e2e.py --scenario scenario-a-happy-path --mode manifest
```

Use `--mode file` with human-edited `inputs/test-cases-p2/scenario-*/e2e_feedback/round_*.json`, or `--mode interactive`. See `results/p2/e2e/README.md`.

### Project 2 — Frontend (Vite landing; proxies API)
```bash
cd frontend && npm install && npm run dev
```
Open **http://localhost:5180** (frontend dev uses **5180** so it does not clash with other apps on Vite’s default **5173**). With the backend on port 8000, the dev server proxies `/sessions`, `/reports`, `/gates`, and `/health` to the API. See `frontend/README.md` for shadcn paths and adding components.

### Run full evaluation suite (live — calls API)
```bash
python scripts/run_eval.py --all
```

### Run specific test case
```bash
python scripts/run_eval.py --tc tc-01-perfect
```

### Run specific dimension
```bash
python scripts/run_eval.py --dimension schema --tc tc-01-perfect
```

### Cost-saving workflow (generate once, replay free)
```bash
# Step 1: Generate outputs for all test cases — 1 API call per TC
python scripts/run_eval.py --generate

# Step 2: Evaluate cached outputs — no API calls, $0 cost
python scripts/run_eval.py --replay --dimension schema
python scripts/run_eval.py --replay --dimension rubric
python scripts/run_eval.py --replay --dimension edge

# Re-run Step 2 unlimited times after changing validator, rubric logic, or expectations.
# Only re-run Step 1 when the prompt changes.
```

Every eval run prints a **cost summary** (API calls, tokens, estimated USD).
Outputs are cached in `outputs/{prompt-version}/` and versioned by prompt.

### Run unit tests
```bash
pytest tests/
```

Unit tests use a **mocked Anthropic client** — no API key or tokens needed.
They verify code correctness (JSON extraction, retry logic, schema validation, logging)
independently from prompt/output quality, which is covered by the eval suite above.

---

## The 8-Step PM Reasoning Process

Every input — no matter how vague — goes through this exact sequence:

```
1. EXTRACT        → What is being built, for whom, why
2. CLASSIFY       → Project type (A through F)
3. CONSTRAINTS    → Hard vs soft constraints
4. ASSUMPTIONS    → Log every gap with PMI basis
5. DECOMPOSE      → Phases → Milestones → Tasks
6. TASKS          → Specific, assignable, time-bounded
7. RISKS          → PMI Risk Management (PMBOK 11.2)
8. STAFFING       → PMI Resource Management (PMBOK 9.2)
```

---

## Evaluation Summary

| Dimension | What It Tests | Automated? |
|-----------|--------------|------------|
| Schema Validation | Output structure correctness | Yes |
| Consistency | Same input = same output (3 runs on TC-01) | Yes |
| Reasoning Quality | Rubric scored 1-5 per dimension | Semi-manual |
| Edge Cases | 10 test cases across input spectrum | Yes |
| PM Comparison | Agent vs manual PM output | Manual |

Target metrics (see [docs/EVALUATION_RUBRIC.md](docs/EVALUATION_RUBRIC.md) for full criteria):
- Schema pass rate: **100%**
- Consistency: variance **< 15**, all scores in same **10-point** band, identical type + SDLC (stricter **< 5** variance also desirable)
- Rubric average: **> 3.5 / 5**
- Edge case pass rate: **> 80%**

---

## Prompt Versioning

Every prompt change is committed to git with this format:
```
prompt(v2): tighten assumption log format

- Added PMI basis requirement to every assumption
- Changed risk_if_wrong to include consequence string
- Tested on TC-01 through TC-05, rubric improved 3.2→3.8
```

See `prompts/README.md` for full history.
