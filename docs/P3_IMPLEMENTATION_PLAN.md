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
[Planning]  [Risk]  Haiku / Haiku — run in PARALLEL via asyncio.gather
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

**Model selection — all agents use Haiku**
| Agent | Model | Reason |
|---|---|---|
| Use Case | Haiku | Simple extraction — actors, UCs, relationships from structured text |
| Intake | Haiku | Classification + constraint extraction — pattern matching, not reasoning |
| Planning | Haiku | WBS decomposition — focused prompt + KB slice keeps context small enough for Haiku |
| Risk | Haiku | Checklist application against known patterns — fast lookup |
| Staffing | Haiku | Rule enforcement (80%/25%/10-15% caps) — arithmetic, not reasoning |
| Synthesis | Haiku | Consistency check + final assembly — all agents use Haiku for cost and latency uniformity |

All 6 agents use Haiku. This is the lowest-latency, lowest-cost configuration.
If output quality is insufficient on eval, upgrade individual agents to Sonnet selectively.

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
I/O anywhere in the hot path.

**LangGraph for orchestration** — `StateGraph` handles node sequencing, conditional intake
gate, and checkpoint/resume. `AsyncSqliteSaver` writes state after every node with zero
custom persistence code. Refinement re-entry uses `aupdate_state(as_node=X)` + `ainvoke(None)`
to replay only the downstream nodes — no hand-rolled routing logic.

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

Model assignments (all Haiku):
- `UseCaseAgent` → Haiku, max_tokens=2000
- `IntakeAgent` → Haiku, max_tokens=4000
- `PlanningAgent` → Haiku, max_tokens=6000
- `RiskAgent` → Haiku, max_tokens=3000
- `StaffingAgent` → Haiku, max_tokens=4000
- `SynthesisAgent` → Haiku, max_tokens=6000

### Step 5 — `agent/rag_client.py`
`KBRetriever` class. Interface designed for Pinecone swap later:
- `get_for_agent(agent_name, project_type=None) -> Optional[str]`
- Planning → templates, filtered to matching TYPE section (cuts context ~60%)
- Risk → full risks.md
- Staffing → full role-definitions.md
- Others → None (no KB needed)
- `_filter_templates_for_type(project_type)` → keyword-slice by TYPE_X header

### Step 6a — `agent/pm_confidence.py` (new)
Pure Python module — no LLM, fully testable in isolation.

```python
def compute_confidence(
    assumption_count: int,
    high_risk_count: int,
    critical_risk_count: int,
    unknown_constraints: int,
    input_quality: str,          # "HIGH" | "MEDIUM" | "LOW" | None
    sdlc_approach: str,          # "Waterfall" | "Hybrid" | "Adaptive"
    project_type: str,           # "TYPE_A" … "TYPE_F"
    total_duration_weeks: float,
) -> dict:                       # {score: float, deductions: [...], interpretation: str}
```

Implements the exact 4-step formula from `synthesis_v1.0.txt` (deductions → raw_score → hard caps → floor).
Called inside `synthesis_node` after the LLM returns. The LLM-generated `deductions` text and
`interpretation` string are kept; only the numeric `score` is replaced with the Python result.

### Step 6b — `agent/orchestrator.py`
**LangGraph `StateGraph`** with `AsyncSqliteSaver` checkpointer.

#### PipelineState TypedDict
```python
class PipelineState(TypedDict):
    raw_brief: str
    session_id: str
    user_id: str
    use_case_artifact:     Optional[dict]
    intake_artifact:       Optional[dict]
    planning_artifact:     Optional[dict]
    risk_artifact:         Optional[dict]
    staffing_artifact:     Optional[dict]
    synthesis_artifact:    Optional[dict]
    token_tally:           dict            # accumulated with operator.add across nodes
    intake_gate_triggered: bool
    intake_gate_reason:    Optional[str]
```

#### Graph topology
```
START → use_case_node → intake_node →(gate?)→ planning_risk_node → staffing_node → synthesis_node → END
                                         ↓ "interrupt"
                                        END
```

5 nodes (Planning and Risk combined into one to keep the graph simple):

| Node | Description |
|------|-------------|
| `use_case_node` | Runs UseCaseAgent async |
| `intake_node` | Runs IntakeAgent async |
| `planning_risk_node` | `asyncio.gather(PlanningAgent, RiskAgent)` — parallel inside one node |
| `staffing_node` | Runs StaffingAgent async |
| `synthesis_node` | Runs SynthesisAgent async, then calls `compute_confidence()` to replace numeric score |

#### Intake gate — conditional edge (not a node)
```python
def intake_gate_router(state: PipelineState) -> Literal["continue", "interrupt"]:
    brief = state["intake_artifact"]
    assumptions = len(brief.get("assumption_log", []))
    quality = brief.get("input_quality_signal", "HIGH")
    if assumptions > 5 or quality == "LOW":
        return "interrupt"   # END — API surfaces gate_triggered to frontend
    return "continue"        # → planning_risk_node
```

#### Checkpointing — `AsyncSqliteSaver`
```python
checkpointer = AsyncSqliteSaver.from_conn_string("sessions/p3_checkpoints.db")
graph = build_graph().compile(checkpointer=checkpointer)
```
Thread ID = `"{user_id}:{session_id}"`. State is saved automatically after every node.
Replaces all file-based checkpoint logic — no custom save/load functions needed.

#### Refinement routing — `aupdate_state` + `ainvoke`
```python
REFINEMENT_TARGETS: dict[str, tuple[str, list[str]]] = {
    "pm_confidence_score":  ("staffing_node",      ["synthesis_artifact"]),
    "staffing_plan":        ("planning_risk_node",  ["staffing_artifact", "synthesis_artifact"]),
    "open_questions":       ("planning_risk_node",  ["staffing_artifact", "synthesis_artifact"]),
    "risk_register":        ("intake_node",         ["planning_artifact", "risk_artifact",
                                                     "staffing_artifact", "synthesis_artifact"]),
    "project_plan":         ("intake_node",         ["planning_artifact", "risk_artifact",
                                                     "staffing_artifact", "synthesis_artifact"]),
    "assumption_log":       ("use_case_node",       ["intake_artifact", "planning_artifact",
                                                     "risk_artifact", "staffing_artifact",
                                                     "synthesis_artifact"]),
}

async def refine(self, section: str, session_id: str, user_id: str, ...) -> PipelineResult:
    as_node, fields = REFINEMENT_TARGETS[section]
    config = {"configurable": {"thread_id": f"{user_id}:{session_id}"}}
    # Rewind graph to after `as_node`, clearing all downstream artifacts
    await self._graph.aupdate_state(config, {f: None for f in fields}, as_node=as_node)
    # Resume — only downstream nodes re-run
    final_state = await self._graph.ainvoke(None, config)
    return _assemble_result(final_state)
```

#### `PipelineOrchestrator` class interface
- `async run(raw_brief, session_id, user_id) -> PipelineResult`
- `async refine(section, session_id, user_id, feedback) -> PipelineResult`
- `async delete_run(session_id, user_id)` — deletes SQLite thread (called on explicit retry or expiry)

### Step 7 — Modify `backend/api/db/store.py` (simplified)
LangGraph's `AsyncSqliteSaver` handles save/load. Only one new function needed:
- `delete_p3_checkpoint(user_id, session_id)` — deletes the LangGraph thread entry from
  `sessions/p3_checkpoints.db` so a clean retry can start from scratch.

No `save_checkpoint` / `load_checkpoint` file functions needed.

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
Follow the exact `unittest.mock.patch` pattern from `tests/p2/`. Key mock targets:
- `agent.agents.intake_agent.IntakeAgent.run_async` — for orchestrator node tests
- `agent.orchestrator.PipelineOrchestrator.run` — for route-level tests
- LangGraph checkpointer: use `MemorySaver` (in-memory) in all tests instead of `AsyncSqliteSaver`
  so tests are isolated, stateless, and need no temp files

```
tests/p3/__init__.py
tests/p3/conftest.py                    # mock artifacts, MemorySaver fixture, mock_anthropic_client
tests/p3/test_partial_schemas.py        # pure Pydantic validation, no mocks
tests/p3/test_pm_confidence.py          # arithmetic correctness — no mocks, pure function tests
tests/p3/test_base_agent.py             # run/run_async with mock_anthropic_client
tests/p3/test_use_case_agent.py
tests/p3/test_intake_agent.py
tests/p3/test_planning_agent.py
tests/p3/test_risk_agent.py
tests/p3/test_staffing_agent.py
tests/p3/test_synthesis_agent.py
tests/p3/test_orchestrator_pipeline.py  # full pipeline happy path, all agents mocked
tests/p3/test_intake_gate.py            # gate fires (>5 assumptions) → state.intake_gate_triggered
tests/p3/test_p3_refinement_routing.py  # all 5 REFINEMENT_TARGETS → correct as_node + fields cleared
tests/p3/test_drawio_generator.py       # deterministic XML output, no LLM
```

Also add `make test-p3` to Makefile: `pytest tests/p3/ -v`

---

## Files Changed / Created

**New files:**
- `schemas/partial_schemas.py`
- `agent/base_agent.py`
- `agent/pm_confidence.py`        ← NEW: pure Python confidence score (testable in isolation)
- `agent/orchestrator.py`         ← LangGraph StateGraph + PipelineOrchestrator
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
- `backend/api/db/store.py` — add `delete_p3_checkpoint()` only (LangGraph handles save/load)
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
   Test with tc-09 and tc-10 (largest inputs) before shipping. Set `max_tokens=8192` for Synthesis.
2. **Prompt quality for split agents** — each focused prompt needs its own eval run
   (`make eval-generate` with the new orchestrator) before committing. Intake is the critical path.
3. **Async in FastAPI** — `generate_report` must be `async def`; verify no sync blocking calls
   remain inside the orchestrator (`AsyncAnthropic` client required for all `run_async()` calls).
4. **LangGraph SQLite thread cleanup** — threads from failed/abandoned runs accumulate in
   `p3_checkpoints.db`. `delete_p3_checkpoint()` must be called on both success and explicit
   retry, not just success. Add a TTL cleanup job or periodic purge for abandoned threads.
5. **LangGraph refinement rewind** — `aupdate_state(as_node=X)` rewinds to after node X.
   If X is `"intake_node"`, the graph resumes from `planning_risk_node`. Verify the correct
   `as_node` for each refinement target — using the wrong node name silently re-runs too much
   or too little. Cover all 5 `REFINEMENT_TARGETS` cases in `test_p3_refinement_routing.py`.
6. **pm_confidence.py score vs LLM score** — the Python score replaces only the numeric value;
   the LLM-generated deductions text and interpretation may reference the wrong number after
   replacement. Add a post-replacement check to update the `interpretation` string with the
   correct final score.
