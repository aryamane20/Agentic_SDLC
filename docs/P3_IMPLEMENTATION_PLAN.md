# P3 Multi-Agent Pipeline — Implementation Plan

## Context

P2 is complete: FastAPI + HITL gates + React frontend all working. P3 replaces the single
`PMAgent.run()` call with a 6-agent orchestrated pipeline. The P3 design is described in full
in the user's message. This plan covers: what to build first, how agents stay consistent,
how to keep latency low via parallelism, and how to cut token costs by ~40–50% vs P2.

The one-line API change: `reports.py` replaces `agent.run(brief)` with
`await orchestrator.run(brief, session_id, user_id)`. Everything else (gates, sessions, refine,
frontend, validation) stays structurally unchanged.

---

## Agent Pipeline

```
Raw Brief
  ↓
[Use Case Agent]   Haiku, ~800 tokens prompt, no KB
  ↓ checkpoint
[Intake Agent]     Haiku, ~3500 tokens prompt, no KB   ← gate: >5 assumptions or LOW quality
  ↓ checkpoint
[Planning]  [Risk]  Sonnet / Haiku — run in PARALLEL via asyncio.gather
  ↓ both checkpoint
[Staffing Agent]   Haiku, ~1200 tokens prompt, staffing KB only (~3KB)
  ↓ checkpoint
[Synthesis Agent]  Sonnet, ~1000 tokens prompt, no KB  ← gate: consistency issues
  ↓
Final PMReport (same schema as P2 — backward compatible)
```

**Gate positions:** post-Intake (if confidence too low or >5 assumptions) and post-Synthesis
(if cross-section consistency issues). Existing `evaluate_gate()` from `approval_gate.py`
runs on the final assembled report unchanged.

---

## Latency Optimization Strategy

### 1. Pipeline & Architecture

**Model selection by task complexity**
| Agent | Model | Reason |
|---|---|---|
| Use Case | Haiku | Simple extraction — actors, UCs, relationships from structured text |
| Intake | Haiku | Classification + constraint extraction — pattern matching, not reasoning |
| Planning | Sonnet | WBS decomposition requires multi-step reasoning across dependencies |
| Risk | Haiku | Checklist application against known patterns — fast lookup |
| Staffing | Haiku | Rule enforcement (80%/25%/10-15% caps) — arithmetic, not reasoning |
| Synthesis | Sonnet | Cross-artifact consistency check requires holding 5 artifacts in mind simultaneously |

Never use Sonnet when Haiku can meet quality bar. The Planning+Risk parallel step means
Sonnet (Planning) and Haiku (Risk) run simultaneously — no Sonnet latency penalty for Risk.

**Merge micro-decisions** — Intake runs all 4 steps (extract → classify → constraints → assumptions)
in one single prompt call, not 4 sequential calls. Same for Staffing (allocation + viability in
one call). This eliminates 3–4 unnecessary round-trips compared to a naive sequential approach.

**Parallelization** — Planning and Risk are independent after Intake. Always run via
`asyncio.gather()`. This cuts the sequential 6-agent chain down to effectively 5 serial steps
(Use Case → Intake → [Planning+Risk] → Staffing → Synthesis). The parallel step saves the
latency of whichever agent is faster (Risk/Haiku completes well before Planning/Sonnet).

**Prompt caching** — Mark system prompt and KB blocks with `cache_control: ephemeral`.
On repeated calls (same agent, same KB), the pre-fill phase is skipped entirely. This is the
biggest single latency win for high-throughput scenarios. Cache TTL is 5 minutes on Anthropic.

**Output length discipline** — Each agent's output contract requests only its partial schema,
not the full PMReport. Intake outputs ~1,500 tokens; Planning ~3,000; Risk ~1,500; Staffing
~1,500; Synthesis ~2,000. Compare to P2's monolithic ~8,000 token output. Smaller outputs
= faster time-to-last-token at every stage.

### 2. Infrastructure

**Co-location** — Deploy FastAPI backend in the same AWS/GCP region as the Anthropic API
endpoint. Network latency between app server and LLM API adds up across 6 agent calls.
For production: us-east-1 (AWS) or us-central1 (GCP) matches Anthropic's primary region.

**Async throughout** — `AsyncAnthropic` client in `BaseAgent.run_async()`, `async def` on
the FastAPI route, `asyncio.gather()` for the parallel step. No `time.sleep()` or blocking
I/O anywhere in the hot path. Checkpoint writes use `tempfile` + atomic replace (non-blocking).

**Native client, no framework overhead** — Direct `anthropic` Python SDK, not LangChain or
similar. Frameworks add per-call overhead (middleware, callback chains) that accumulates
across 6 agents.

### 3. User Perception (Frontend)

**Streaming per-agent status** — The orchestrator emits stage-completion events as each
agent finishes. The frontend shows a live progress indicator:

```
[ Use Case ✓ ] [ Intake ✓ ] [ Planning... ] [ Risk... ] [ Staffing ] [ Synthesis ]
                                    ↑ streaming update as each stage completes
```

Implementation: add a `POST /generate` response that returns immediately with a `pipeline_id`,
then a `GET /pipeline-status/{pipeline_id}` SSE endpoint the frontend polls. Each
`_checkpoint()` write in the orchestrator also publishes a status event.

**Token streaming for Synthesis** — Synthesis is the longest Sonnet call and produces the
final visible output. Stream its tokens directly to the frontend using the Anthropic streaming
API (`stream=True`) so the PM sees the report assembling in real time rather than waiting
for the full response.

**Filler states** — While any agent is running, the frontend shows:
- Stage name + elapsed time ticker ("Planning... 4s")
- Intermediate artifact previews once available (e.g., use case diagram renders as soon as
  Use Case Agent completes, before the rest of the pipeline finishes)
- The use case diagram (generated by `drawio_generator.py`) can be displayed immediately
  after Stage 1 — gives the PM something meaningful to review during the 20–30s pipeline run

**Perceived latency budget** — Target: first meaningful content on screen within 5s (use case
diagram), full report within 30s for a typical brief. The parallel Planning+Risk step is the
key to hitting this; sequential would push typical runs to 45–60s.

---

## Cost Analysis

| Metric | P2 (monolithic) | P3 (multi-agent) | Delta |
|---|---|---|---|
| System context / call | ~16,550 tokens (full prompt + all 3 KB) | Split: largest single call ~5,500 tokens | −67% per agent |
| Output tokens / call | ~8,000 (full PMReport) | ~500–3,000 per partial | −60% per agent |
| Models | Haiku (with large context) | Haiku × 4, Sonnet × 2 | Haiku is ~15× cheaper |
| Parallel step | None | Planning + Risk run simultaneously | −latency, not cost |
| KB injected | All 3 files to every call (~4,350 tokens) | Each agent gets only its slice | Planning ~2,050, Risk ~1,580, Staffing ~720 |
| Refinement (targeted) | Full re-run every time | Only affected agents re-run | Risk-only refine = 3 agents not 6 |

**Estimated full pipeline cost vs P2:** ~30,000 input + 8,700 output vs P2's ~16,550 + 8,000.
Raw token count is higher but effective cost is lower because 4 of 6 agents use Haiku, and
the Planning+Risk parallel step eliminates sequential latency. Refinement cost drops ~50%.

---

## Token-Saving Techniques to Implement

1. **Prompt caching on system blocks** — mark both the system prompt block and KB block with
   `cache_control: {"type": "ephemeral"}` per agent. System prompts are identical across all
   requests to the same agent → high cache hit rate.
2. **KB slicing by project type** — `KBRetriever._filter_templates_for_type()` returns only the
   relevant TYPE_A/B/C/D/E/F section from templates.md. Cuts Planning context by ~60%.
3. **Partial schemas** — each agent produces only its section (not full PMReport). Output tokens
   per call are smaller.
4. **Model selection**: Use Case (Haiku), Intake (Haiku), Planning (Sonnet — complex reasoning),
   Risk (Haiku — pattern matching), Staffing (Haiku — rule enforcement), Synthesis (Sonnet —
   consistency check across all artifacts).
5. **`max_tokens` per agent** — size to actual output needs. Intake: 4,000. Planning: 6,000.
   Risk: 3,000. Staffing: 4,000. Synthesis: 6,000. Not all set to 16,000 like P2.

---

## Intermediate Artifacts (What Gets Passed Between Agents)

Each checkpoint written to `sessions/_checkpoints/{user_id}/{session_id}/{stage}.json`.

| Artifact | Produced by | Consumed by | Key fields |
|---|---|---|---|
| `use_case_model.json` | Use Case Agent | All downstream | actors[], use_cases[], relationships[], diagram_xml, input_quality_signal |
| `structured_brief.json` | Intake | Planning, Risk, Staffing, Synthesis | project_understanding, assumption_log, report_metadata (project_type, sdlc), constraints{hard,soft,nfr}, open_questions_pre_planning |
| `project_plan.json` | Planning | Staffing, Synthesis | project_plan (phases+tasks), use_case_task_mapping{UC_id: [task_ids]} |
| `risk_register.json` | Risk | Staffing, Synthesis | risk_register[], risk_use_case_mapping, critical_path_risk_flags[task_ids] |
| `staffing_plan.json` | Staffing | Synthesis | staffing_plan[], open_questions[], pm_confidence_score, project_viability, actor_role_mapping |

`constraints` is a new intermediate field not in PMReport — Intake extracts it so Planning/Risk
don't re-read the raw brief for constraint data.

---

## Consistency Enforcement (Synthesis Agent Responsibilities)

Synthesis receives all 5 artifacts and applies these rules before assembling the final PMReport:

1. **Actor ↔ Role coverage** — every non-external actor in `use_case_model` must map to at
   least one role in `staffing_plan`. Gap → inject missing role with estimated hours.
2. **CRITICAL risk → staffing flag** — roles owning CRITICAL-risk tasks must have
   `critical_path: true` in staffing. Auto-corrected if missing.
3. **Use case task coverage** — every use case ID must appear in `use_case_task_mapping`.
   Not auto-corrected; added to `open_questions` instead.
4. **pm_confidence_score recomputation** — Synthesis recomputes score from visible
   counts and applies hard caps. Replaces the Staffing agent's self-reported score.
5. **Timeline achievability** — sum(task effort_hours) / productive capacity check.
   Flags warning if math doesn't close.

---

## Build Order (Each Step Independently Shippable)

### Step 1 — `schemas/partial_schemas.py`
Pydantic models for each agent's output. No new code dependencies — imports only from
`schemas/output_schema.py`. Includes: `UseCaseModel`, `StructuredBrief`, `ConstraintsBlock`,
`ProjectPlanArtifact`, `RiskRegisterArtifact`, `StaffingPlanArtifact`, `SynthesisResult`,
`PipelineResult`, `TokenTally`.

### Step 2 — `agent/base_agent.py`
`BaseAgent` class with:
- `__init__(agent_name, prompt_path, model, max_tokens, temperature)`
- `_build_system_blocks(kb_content=None)` — returns system blocks with `cache_control: ephemeral`
  on both prompt and KB blocks
- `run(context, use_cache=True)` — sync, returns `{artifact, input_tokens, output_tokens, ...}`
- `run_async(context, use_cache=True)` — async variant using `AsyncAnthropic` for parallel step
- `_extract_json(raw)` — copy verbatim from `agent/main.py` (same logic)
- `_build_user_message(context)` — abstract, overridden in each subclass

KB content injected via `context["_kb_content"]` key (private convention, set by orchestrator).

### Step 3 — `prompts/agents/` (6 new prompt files)
Extract from `v1.6.4_system.txt` using these line boundaries:
- `intake_v1.0.txt`: Steps 1–4 (~lines 35–344), add StructuredBrief output contract, ~350 lines
- `planning_v1.0.txt`: Steps 5–6 (~lines 345–461), add ProjectPlanArtifact output contract, ~200 lines
- `risk_v1.0.txt`: Step 7 (~lines 462–557), add RiskRegisterArtifact output contract, ~175 lines
- `staffing_v1.0.txt`: Step 8 (~lines 558–652), add StaffingPlanArtifact output contract, ~175 lines
- `use_case_v1.0.txt`: NEW — UML use case extraction, actor/UC/relationship JSON, ~150 lines
- `synthesis_v1.0.txt`: NEW — consistency check rules, final assembly, SynthesisResult JSON, ~200 lines

Each inherits core principles from v1.6.4 (PMI-grounded, no rejection, hard caps, JSON-only).
None has the 8-step overview — only its own steps + partial output contract.

### Step 4 — `agent/agents/` (6 thin subclasses)
`agent/agents/__init__.py` + one file per agent. Each overrides `_build_user_message()` and
calls `super().__init__(agent_name=..., prompt_path=..., model=..., max_tokens=...)`.

Model assignments:
- `UseCaseAgent` → Haiku, max_tokens=2000
- `IntakeAgent` → Haiku, max_tokens=4000
- `PlanningAgent` → Sonnet, max_tokens=6000
- `RiskAgent` → Haiku, max_tokens=3000
- `StaffingAgent` → Haiku, max_tokens=4000
- `SynthesisAgent` → Sonnet, max_tokens=6000

### Step 5 — `agent/rag_client.py`
`KBRetriever` class. Interface designed for Pinecone swap later:
- `get_for_agent(agent_name, project_type=None) -> Optional[str]`
- Planning → templates, filtered to matching TYPE section (cuts context ~60%)
- Risk → full risks.md
- Staffing → full role-definitions.md
- Others → None (no KB needed)
- `_filter_templates_for_type(project_type)` → keyword-slice by TYPE_X header

### Step 6 — `agent/orchestrator.py`
`PipelineOrchestrator` class with:
- `async run(raw_brief, session_id, user_id, resume_from_stage=None) -> PipelineResult`
- `async refine(section, feedback, session_id, user_id, current_artifacts) -> PipelineResult`
- `_checkpoint(user_id, session_id, stage, data)` — writes to `sessions/_checkpoints/`
- `_load_checkpoints(user_id, session_id, up_to_stage) -> dict` — loads stages up to given stage
- `_check_intake_gate(structured_brief) -> Optional[str]` — >5 assumptions or LOW quality signal

Parallel execution pattern:
```python
plan_task = asyncio.create_task(self.planning_agent.run_async(context={...}))
risk_task  = asyncio.create_task(self.risk_agent.run_async(context={...}))
plan_result, risk_result = await asyncio.gather(plan_task, risk_task)
```

Refinement routing (which agents re-run based on feedback target):
| Feedback section | Re-run from |
|---|---|
| `pm_confidence_score` | synthesis only |
| `staffing_plan`, `open_questions` | staffing → synthesis |
| `risk_register` | risk → staffing → synthesis |
| `project_plan` | planning → (risk + planning parallel) → staffing → synthesis |
| `assumption_log`, `project_understanding` | intake → all downstream |

### Step 7 — Modify `backend/api/db/store.py`
Add 3 functions following the exact atomic write pattern (`tempfile.mkstemp` + replace):
- `save_checkpoint(user_id, session_id, stage, data)` — writes to `sessions/_checkpoints/`
- `load_checkpoint(user_id, session_id, stage) -> Optional[dict]`
- `delete_checkpoints(user_id, session_id)` — called after successful pipeline completion

Checkpoint path: `sessions/_checkpoints/{user_id}/{session_id}/{stage}.json`

### Step 8 — Modify `backend/api/routers/reports.py`
Minimal change (3 lines):
1. Change `generate_report` from `def` to `async def`
2. Replace `agent = _agent_for_version(...)` + `agent.run(composed)` with:
   `pipeline_result = await _orchestrator.run(raw_brief=composed, session_id=..., user_id=...)`
3. Remove the 3-attempt retry loop at router level (orchestrator handles retries per-agent)

Keep unchanged: `classify_input()`, `evaluate_gate()`, `store.save_session()`,
`sync_pm_confidence_metadata_mirrors()`, `_validator.validate()`, `ReportEntry` creation,
revision-based optimistic locking, `extract-document` endpoint.

### Step 9 — `agent/drawio_generator.py`
Pure Python, no LLM:
- `use_case_json_to_drawio_xml(use_case_output: dict) -> str` — build `<mxfile>` XML
  using ElementTree; actors as ellipses, use cases as rounded rects, system boundary as
  rectangle, relationships as edges. Grid layout: actors left column, UCs inside boundary.
- `async render_diagram_png(xml: str) -> Optional[bytes]` — POST to Kroki API
  (`https://kroki.io/drawio/png`) with base64-encoded XML, return PNG bytes.

Use Case Agent calls `use_case_json_to_drawio_xml()` after parsing its LLM output, then
stores `diagram_xml` in the artifact. PNG rendering is best-effort (None on failure).

### Step 10 — `tests/p3/`
Follow the exact `unittest.mock.patch` pattern from `tests/p2/`. Mock targets:
- `agent.agents.intake_agent.IntakeAgent.run_async` (for orchestrator tests)
- `agent.orchestrator.PipelineOrchestrator.run` (for route tests)
- `backend.api.db.store.save_checkpoint` (for checkpoint tests)

Files:
```
tests/p3/__init__.py
tests/p3/conftest.py              # mock_use_case_result, mock_structured_brief fixtures
tests/p3/test_partial_schemas.py  # pure Pydantic validation, no mocks
tests/p3/test_base_agent.py       # run/run_async with mock_anthropic_client
tests/p3/test_use_case_agent.py
tests/p3/test_intake_agent.py
tests/p3/test_planning_agent.py
tests/p3/test_risk_agent.py
tests/p3/test_staffing_agent.py
tests/p3/test_synthesis_agent.py
tests/p3/test_orchestrator_pipeline.py  # full pipeline happy path, mocked agents
tests/p3/test_checkpoint_resume.py       # gate fires → resume from checkpoint
tests/p3/test_p3_refinement_routing.py  # section → correct agents re-run
tests/p3/test_drawio_generator.py        # deterministic XML, no LLM
```

Also add `make test-p3` to Makefile: `pytest tests/p3/ -v`

---

## Files Changed / Created

**New files:**
- `schemas/partial_schemas.py`
- `agent/base_agent.py`
- `agent/orchestrator.py`
- `agent/rag_client.py`
- `agent/drawio_generator.py`
- `agent/agents/__init__.py`
- `agent/agents/use_case_agent.py`
- `agent/agents/intake_agent.py`
- `agent/agents/planning_agent.py`
- `agent/agents/risk_agent.py`
- `agent/agents/staffing_agent.py`
- `agent/agents/synthesis_agent.py`
- `prompts/agents/use_case_v1.0.txt`
- `prompts/agents/intake_v1.0.txt`
- `prompts/agents/planning_v1.0.txt`
- `prompts/agents/risk_v1.0.txt`
- `prompts/agents/staffing_v1.0.txt`
- `prompts/agents/synthesis_v1.0.txt`
- `tests/p3/` (12 files)

**Modified files:**
- `backend/api/db/store.py` — add 3 checkpoint functions
- `backend/api/routers/reports.py` — replace agent.run with orchestrator.run, make async
- `Makefile` — add `make test-p3`

**Unchanged (backward compatible):**
- `schemas/output_schema.py` — final PMReport schema identical
- `backend/api/services/approval_gate.py` — evaluate_gate() reused as-is
- `backend/api/routers/gates.py`, `refine.py`, `sessions.py` — no changes in Phase 1
- `agent/main.py` — kept for P1/P2 compatibility; P3 routes around it
- All P1 and P2 tests — must stay green throughout

---

## Verification Steps

1. `make test` — all existing P1/P2 tests still pass (no regressions)
2. `make test-p3` — all new P3 tests pass with mocked agents
3. Start API + frontend: `make api` and `make frontend`
4. Submit a test brief via the UI — watch the pipeline complete end-to-end
5. Check `sessions/_checkpoints/` for intermediate artifacts after generation
6. Check that `evaluate_gate()` still fires correctly on the final assembled report
7. Submit refinement feedback targeting the risk section — verify only Risk+Staffing+Synthesis re-run (confirm via Langfuse traces or checkpoint timestamps)
8. `make eval-replay` — golden dataset rubric scores must not regress vs P2 baseline

---

## Key Risks

1. **Synthesis context bloat** — all 5 artifacts in one call can reach 12,000+ input tokens.
   Test with tc-09 and tc-10 (largest inputs) before shipping. Set `max_tokens=6000` for Synthesis.
2. **Prompt quality for split agents** — each focused prompt needs its own eval run
   (`make eval-generate` with the new orchestrator) before committing. Intake is the critical path.
3. **Async in FastAPI** — `generate_report` must be `async def`; verify no sync blocking calls
   remain inside the orchestrator (Anthropic `AsyncAnthropic` client required for `run_async()`).
4. **Cache invalidation** — checkpoints from a failed run must be cleaned up before a retry.
   `delete_checkpoints()` must be called on both success and explicit retry, not just success.
