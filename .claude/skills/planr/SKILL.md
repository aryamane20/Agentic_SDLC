---
name: planr
description: >
  PLANR project orientation. Load this skill at the start of any session
  working on the PLANR codebase — agent, backend API, frontend, prompts,
  tests, or evaluation. Also triggers for: understanding how the 8-step
  reasoning works, navigating the project structure, running tests or evals,
  adding new features, or debugging any part of the stack.
---

# PLANR — Project Orientation

Load this at the start of any session. For HITL-specific work (gates,
refinement, the approval flow), also load `.claude/skills/hitl/SKILL.md`.

---

## What This Is

PLANR is an AI agent that replicates the thinking of a senior internal PM.
Given raw project requirements (any quality), it runs an 8-step reasoning
process and outputs a structured JSON plan: intent extraction → project
classification → assumption logging → WBS decomposition → risk register →
staffing plan → open questions → PM confidence score.

The project spans three stages:
- **P1 (done):** Single agent, embedded knowledge, deterministic JSON output
- **P2 (active):** FastAPI backend + HITL approval gates + React frontend
- **P3 (designed):** Multi-agent pipeline + RAG knowledge retrieval

Full system design: `docs/ARCHITECTURE.md`

---

## Directory Map

```
agent/          PM agent core (main.py, runner.py, validator.py)
backend/        FastAPI HITL API (routers/, services/, models/, db/)
frontend/       React + Vite UI (hooks/, components/, pages/, lib/)
prompts/        Versioned system prompts (active: v1.6.2_system.txt)
schemas/        Shared Pydantic models (input_schema.py, output_schema.py)
knowledge-base/ PMI-grounded PM domain knowledge (templates, risks, staffing)
tests/          Full test suite — run from repo root
scripts/        Eval harness (run_eval.py) and log analysis
docs/           Architecture, evaluation rubric, pre-mortem
inputs/         10 test cases (tc-01 to tc-10)
outputs/        Cached eval outputs — versioned by prompt, gitignored
logs/           Run logs — gitignored except logs/samples/
sessions/       User session JSON store — gitignored
```

---

## Key Patterns to Know

**Prompt versioning is immutable.** Never edit an existing `prompts/v*.txt`.
Create a new version and update `agent/main.py` to point to it. The active
version is `v1.6.2`. Changelog lives in `prompts/PROMPT_CHANGELOG.md`.

**The agent output is JSON only.** `PMAgent.run()` returns a validated dict.
`agent/validator.py` applies schema + business rules. `agent/main.py` applies
hard caps after validation. Both are always called in sequence.

**Gate is a warning, not a lock.** When the HITL gate fires, the PM can still
refine with feedback — that feedback IS their human-in-the-loop response. The
gate is re-evaluated on every new report. Approve is the only formal close.
See `.claude/skills/hitl/SKILL.md` for the full state machine.

**Locked sections on refinement.** Steps 5–8 are re-run on refine; Steps 1–4
(`project_understanding`, `assumption_log`, classification metadata) are locked
from the prior report. `backend/api/services/refinement.py` handles this.

**Tests are mocked.** The real Anthropic client is never called in tests.
`conftest.py` provides a `mock_anthropic_client` fixture. Any test that
instantiates a real `PMAgent` without mocking will fail in restricted
environments (no API key / proxy). Use the existing mock pattern.

**Evaluation is two-phase.** `make eval-generate` calls the API (costs tokens)
and saves outputs to `outputs/`. `make eval-replay` scores those cached outputs
for free. Never regenerate when you can replay.

---

## Common Commands

```bash
make install          # Python deps (agent + backend)
make install-frontend # npm deps

make api              # FastAPI on :8000
make frontend         # Vite on :5180

make test             # Full test suite
make test-hitl        # HITL tests only (fast, no mocks needed beyond store)
make test-fast        # Skip slow eval tests

make eval-replay      # Score cached outputs (free)
make eval-generate    # Fresh generation (uses API credits)
```

---

## Active Versions

| Layer | Version | File |
|-------|---------|------|
| System prompt | v1.6.2 | `prompts/v1.6.2_system.txt` |
| Output schema | current | `schemas/output_schema.py` |
| Backend API | 0.1.0 | `backend/api/main.py` |
| Frontend | 0.1.0 | `frontend/package.json` |

---

## Sub-Skills

| Task | Load |
|------|------|
| HITL gates, refinement, approve flow | `.claude/skills/hitl/SKILL.md` |
| General PLANR orientation | this file |
