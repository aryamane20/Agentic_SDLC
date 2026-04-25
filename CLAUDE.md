# PLANR — Claude Context

## What This Is

PLANR is an AI agent that replicates a senior internal PM's thinking process.
Raw requirements in → validated JSON plan out (project plan + risk register + staffing plan).
Built as a course project evolving across three stages:

- **P1 (done):** Single agent, embedded knowledge, deterministic JSON output
- **P2 (done):** FastAPI HITL backend + React/Vite frontend + approval gates
- **P3 (designed):** Multi-agent pipeline (Use Case → Intake → Planning → Risk → Staffing → Synthesis) + RAG

Full design: `docs/ARCHITECTURE.md`

---

## The Two-Layer Brain (most important pattern)

The system prompt is split into two separate layers compiled at runtime by `_build_system_context()`:

| Layer | What it encodes | Lives in |
|-------|----------------|----------|
| **Role** | WHO the agent is and HOW it reasons (8-step process, PMI heuristics, output contract) | `prompts/v1.6.4_system.txt` |
| **Knowledge Base** | WHAT domain knowledge it draws on (templates, risks, staffing) | `knowledge-base/` |

These are kept separate so reasoning changes and domain knowledge changes can be tracked and evaluated independently in git.

**P3 note:** `_build_system_context()` is an intentional stub. In P3 it will be replaced with RAG retrieval per sub-agent. Do not "improve" the inline loading — the simplicity is deliberate.

---

## Cost-Sensitive Commands

⚠️ These commands call the Anthropic API and cost real tokens:

```bash
make eval-generate        # Generates fresh outputs for all test cases
python scripts/run_eval.py --generate
python scripts/run_eval.py --all
```

✅ These are always free (use cached outputs or mocks):

```bash
make eval-replay          # Scores cached outputs — no API calls
make test                 # Full pytest suite — Anthropic client is mocked
make test-hitl            # HITL tests only — also mocked
```

**Default workflow:** always `eval-replay` first. Only run `eval-generate` when the prompt version changes.

---

## Prompt Versioning Rules

1. **Never edit an existing `prompts/v*.txt`.** Create a new version.
2. Update the active version constant in `agent/main.py` (`MODEL_HAIKU` / `MODEL_SONNET` lines and the default arg in `PMAgent.__init__`).
3. Test on TC-01 through TC-05 minimum before committing.
4. Append to `prompts/PROMPT_CHANGELOG.md`.
5. Commit with this exact format:
   ```
   prompt(vX.Y): short description of change

   - What changed and why
   - Test cases run + rubric score delta (e.g. 3.2→3.8)
   ```

Use `/prompt-bump` to run this as a guided checklist.

---

## Test Philosophy

Two completely separate concerns — do not conflate them:

| Suite | Command | Uses API? | Tests what |
|-------|---------|-----------|-----------|
| Unit tests | `make test` | ❌ mocked | Code correctness (JSON extraction, retry logic, schema validation, logging) |
| Eval suite | `make eval-replay` / `make eval-generate` | ✅ (generate only) | Prompt + output quality across 10 test cases |

All unit tests use `mock_anthropic_client` from `tests/conftest.py`. Never instantiate a real `PMAgent` in pytest — it will fail without an API key.

---

## Running P2 Locally

Backend and frontend must both be running:

```bash
make api        # FastAPI on :8000  (start first)
make frontend   # Vite on :5180     (proxies /sessions, /reports, /gates to :8000)
```

OpenAPI docs: `http://127.0.0.1:8000/docs`

---

## Skills

Load the relevant skill at the start of any session:

| Working on | Load |
|-----------|------|
| Agent, prompts, eval, general orientation | `.claude/skills/planr/SKILL.md` |
| Gates, refinement, HITL API, frontend workflow | `.claude/skills/hitl/SKILL.md` |

---

## Active Versions

| Layer | Version |
|-------|---------|
| System prompt | `v1.6.4` → `prompts/v1.6.4_system.txt` |
| Output schema | `schemas/output_schema.py` |
| Backend API | `0.1.0` |
| Frontend | `0.1.0` |
