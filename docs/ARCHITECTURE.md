# Architecture.md
## PM Digital Twin — Full System Design

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      PM DIGITAL TWIN                             │
│                                                                   │
│   RAW INPUT                                                       │
│   (any format/quality)                                            │
│        │                                                          │
│        ▼                                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    PM BRAIN (LLM)                        │   │
│   │                                                           │   │
│   │  System Prompt (Layer 1 — always active)                 │   │
│   │  ├── Identity & Persona                                   │   │
│   │  ├── 8-Step Reasoning Process                            │   │
│   │  ├── PMI-Grounded Heuristics                             │   │
│   │  ├── Output Contract                                      │   │
│   │  └── Boundaries                                          │   │
│   │                                                           │   │
│   │  Knowledge Base (Layer 2 — inline for Project 1)         │   │
│   │  ├── Project Type Templates (A-F)                        │   │
│   │  ├── Risk Pattern Catalog                                 │   │
│   │  └── Staffing Benchmarks                                 │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                          │
│        ▼                                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  OUTPUT PIPELINE                         │   │
│   │                                                           │   │
│   │  1. Raw LLM Response                                      │   │
│   │  2. JSON Extraction (main.py _extract_json)              │   │
│   │  3. Schema Validation (validator.py)                     │   │
│   │  4. Structured Logging (logger.py)                       │   │
│   │  5. Final Report                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                          │
│        ▼                                                          │
│   INTEGRATED PM REPORT                                            │
│   ├── Project Understanding                                       │
│   ├── Assumption Log                                             │
│   ├── Project Plan (Phases → Milestones → Tasks)                │
│   ├── Risk Register                                              │
│   ├── Staffing Plan                                              │
│   ├── Open Questions                                             │
│   └── PM Confidence Score                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. The Two-Layer Brain

### Layer 1: System Prompt (The Thinking Layer)
**What it encodes:** WHO the agent is and HOW it thinks.
**Lives in:** `prompts/v1.6.4_system.txt` (current active version; prior versions retained for replay)
**Changes when:** Reasoning quality improves through prompt iteration.
**Version controlled:** Yes — every change committed with rubric scores.

The system prompt has 5 components:

| Component | Purpose | Approximate Tokens |
|-----------|---------|-------------------|
| Identity & Persona | Sets PM seniority, domain, style | ~100 |
| 8-Step Reasoning | The exact cognitive sequence | ~600 |
| PMI Heuristics | Decision rules grounded in PMBOK | ~300 |
| Output Contract | Non-negotiable output structure | ~200 |
| Boundaries | What the agent never does | ~100 |
| **Total** | | **~1,300** |

### Layer 2: Knowledge Base (The Domain Layer)
**What it encodes:** WHAT domain knowledge the agent draws on.
**Lives in:** `knowledge-base/` — compiled inline into system prompt for P1.
**Project 1:** Inline in system prompt (no RAG infrastructure).
**Project 3:** Extracted into vector store, retrieved dynamically.

| Knowledge Section | Content | Used In Step |
|-------------------|---------|-------------|
| Project Type Templates | Phase structures per type | Step 5 |
| Risk Pattern Catalog | Known risks per type/constraint | Step 7 |
| Staffing Benchmarks | Role definitions, hour estimates | Step 8 |

**Project 3:** The same KB (and additional BA / use-case guidance as needed) is **retrieved per agent** from a vector store instead of compiled wholesale. The **Use Case Agent** is the first consumer; Intake through Staffing agents query slices relevant to their step, always with access to the **use case model** produced in the zeroth stage.

---

## 3. The 8-Step Reasoning Process (Detailed)

### Step 1: EXTRACT
**Input:** Raw requirement text (any quality)
**Output:** Structured understanding object
**Failure mode:** Hallucinating intent not present in input
**Guard:** Agent must quote specific text that supports each extraction

```
Extracts:
├── primary_goal
├── beneficiary (who internally)
├── trigger (why now)
└── success_definition
```

### Step 2: CLASSIFY
**Input:** Extracted understanding
**Output:** Project type (A-F) + confidence level
**Why it matters:** Classification determines which phase template,
risk patterns, and staffing benchmarks are applied downstream.

```
TYPE A: New Internal Tool Build
TYPE B: Enhancement to Existing System
TYPE C: Data Pipeline / Reporting
TYPE D: System Integration
TYPE E: Migration
TYPE F: Process Automation
```

### Step 3: CONSTRAINT EXTRACTION
**Input:** Full raw text
**Output:** Hard constraints vs soft constraints
**Key rule:** Every UNKNOWN hard constraint triggers an assumption in Step 4.

```
Hard Constraints (cannot change):
├── deadline
├── budget
├── team_size
├── technology_stack
└── compliance_requirements

Soft Constraints (negotiable):
├── preferred_timeline
├── preferred_team
└── nice_to_have_features
```

### Step 4: ASSUMPTION LOG
**Input:** All UNKNOWNs from Steps 1-3
**Output:** Structured assumption log
**PMI Basis:** Every assumption must reference a PMBOK principle.
**This is the most important section for human review.**

Format per assumption:
```
ASSUMPTION #n
  WHAT: [specific assumption]
  WHY: [why this is a reasonable default]
  PMI_BASIS: [PMBOK reference]
  RISK_IF_WRONG: HIGH | MEDIUM | LOW
  CONSEQUENCE: [what breaks if this assumption is wrong]
```

### Step 5: DECOMPOSITION
**Input:** Classification + constraints + assumptions
**Output:** Phase structure with timeline allocation
**PMI Basis:** Work Breakdown Structure (PMBOK 5.4)

Standard phase allocations:
```
Phase 1: Discovery & Design     → 10-15% of timeline (NEVER below 10%)
Phase 2: Core Development       → 35-40%
Phase 3: Integration & Edge     → 20-25%
Phase 4: QA & Testing           → 15-20% (NEVER below 15%)
Phase 5: Deployment & Handoff   → 5-10%
Buffer                          → +15% on all developer estimates
```

### Step 6: TASK GENERATION
**Input:** Phase structure
**Output:** Task list (one assignable unit per task)
**Rule:** Every task must be completable by one role in 1-5 days.

Per task:
```
├── id (T1, T2...)
├── name
├── phase
├── effort_hours
├── owner_role
├── dependencies [T_ids]
└── risk_flag (boolean)
```

### Step 7: RISK IDENTIFICATION
**Input:** Full plan + constraints + project type
**Output:** Risk register sorted by score
**PMI Basis:** Risk Management Plan (PMBOK 11.2)

Mandatory risk checks (always evaluated regardless of input):
```
□ Fixed deadline + undefined scope → Schedule Risk
□ New/unfamiliar technology → Technical Risk
□ External dependencies > 2 → Integration Risk
□ Team < 3 for project > 2 months → Resource Risk
□ No written stakeholder approval → Scope Risk
□ Compliance/security requirements → Compliance Risk
```

Risk scoring matrix:
```
         │ HIGH Impact │ MED Impact │ LOW Impact
─────────┼─────────────┼────────────┼───────────
HIGH Prob│  CRITICAL   │    HIGH    │   MEDIUM
─────────┼─────────────┼────────────┼───────────
MED Prob │    HIGH     │   MEDIUM   │    LOW
─────────┼─────────────┼────────────┼───────────
LOW Prob │   MEDIUM    │    LOW     │    LOW
```

### Step 8: STAFFING
**Input:** Task list + phase structure + risks
**Output:** Staffing plan per role
**PMI Basis:** Resource Management Plan (PMBOK 9.2)

Hard rules:
```
□ No role allocated > 80% (PMI best practice)
□ QA effort ≥ 25% of development effort (PMBOK 8.2)
□ Critical path roles must be full-time
□ Projects > 3 months need backup for every critical path role
□ PM oversight = 10-15% of total project hours
```

---

## 4. Output Schema

See `schemas/output_schema.json` for full JSON Schema definition.

Top-level structure:
```json
{
  "report_metadata": {},
  "project_understanding": {},
  "assumption_log": [],
  "project_plan": { "phases": [{ "tasks": [] }] },
  "risk_register": [],
  "staffing_plan": [],
  "open_questions": [],
  "pm_confidence_score": { "score", "deductions", "interpretation" },
  "project_viability": null | { "viability_status", "gap_type", "gap_amount", "scoping_options" }
}
```

### PM Confidence Score Calculation
See the mandatory deduction table and hard caps in the system prompt (output contract).
Interpretation: 80-100 = high quality; 60-79 = medium; 40-59 = low; 0-39 = very low.

---

## 5. Input Handling

The agent handles all input formats without rejection:

| Input Quality | Agent Behavior |
|--------------|----------------|
| Complete PRD | Minimal assumptions, high confidence score |
| Good brief | Several assumptions, medium-high confidence |
| Vague request | Many assumptions, medium confidence |
| Single sentence | Maximum assumptions, low confidence, all flags raised |
| Contradictory | Flags contradiction explicitly, confidence < 40 |

**The agent NEVER rejects input. Every input produces a full report.**

---

## 6. Technology Stack

| Layer | Technology | Project | Why |
|-------|-----------|---------|-----|
| LLM | Claude Haiku (dev) / Sonnet (eval) | P1–P3 | Consistent structured output |
| Language | Python 3.11+ | P1–P3 | Agent logic, eval scripts, FastAPI backend |
| Validation | Pydantic (`schemas/output_schema.py` `PMReport`) + business rules in `validator.py` | P1 | Schema + PMI-style checks (P2–P3 may add per-artifact models) |
| Logging | Python logging + JSON + Langfuse | P1–P3 | Structured run logs + LLM observability |
| Testing | pytest (mocked API) | P1–P3 | Unit tests without burning API tokens |
| Version Control | Git | P1–P3 | Prompt versioning + code |
| API Backend | FastAPI + Uvicorn | P2–P3 | Async, Pydantic-native, auto OpenAPI docs |
| Frontend | React + Vite + Tailwind CSS | P2–P3 | Fast dev server, utility-first styling |
| UI Components | shadcn/ui + 21st.dev | P2–P3 | Copy-owned components, Radix UI + Tailwind |
| Session Store | JSON files (sessions/) | P2 | Zero-setup MVP persistence, no DB needed |
| Database | PostgreSQL (Supabase) | P3+ | Persistent multi-user storage at scale |
| Vector Store | Pinecone / Weaviate | P3 | RAG retrieval per sub-agent |
| Diagram Rendering | Kroki free API | P3 | draw.io XML → PNG, no auth required |
| Deployment | Railway / Render (backend) + Vercel (frontend) | P3+ | Free tier, public URL |

---

## 7. Project Evolution Path

### Project 1: Single Agent
```
Input → [System Prompt + KB compiled together] → LLM → Parser → Validator → Output
```
Everything in one agent. KB lives in separate files, compiled into context at runtime on every call..

### Project 2: Approval Gates + Refinement Loop

> **Implementation status:** **`backend/` is implemented** (FastAPI + session JSON store + gates + refine MVP). **`frontend/`** is still the target design only. Project 1 core (`agent/`, `scripts/run_eval.py`) remains unchanged.

**Stack:** FastAPI + Uvicorn (backend) · React + Vite + Tailwind CSS + shadcn/ui + 21st.dev (frontend)

**Request flow:**
```
PM submits brief (React UI)
    → POST /reports/generate  (FastAPI)
        → PMAgent.run()  [Project 1 agent — unchanged]
            → approval_gate.py checks output
                → gate fired?  YES → return report + gate details
                → gate clear?  NO  → return report + auto-approved
    → React displays report cards + GateAlert banner (if fired)
        → PM approves   → POST /gates/{id}/decision  { decision: "approve" }
        → PM rejects    → POST /gates/{id}/decision  { decision: "reject" }
        → PM refines    → POST /reports/{id}/refine  { feedback: "..." }
            → refinement.py injects previous report + feedback
                → PMAgent.run() re-runs Steps 5–8 only
                → Steps 1–4 extraction stays locked
            → returns updated report + new gate status
```

**New files (`backend/` + `backend/api/` and `frontend/` sit alongside existing P1 code):**
```
backend/
  requirements.txt          ← fastapi, uvicorn, pydantic, python-dotenv
  api/
    main.py                 ← FastAPI app, CORS, router registration
    routers/
      sessions.py           ← POST /sessions, GET /sessions/{id}
      reports.py            ← POST /reports/generate, GET /reports/{id}
      gates.py              ← GET /gates/{report_id}, POST /gates/{report_id}/decision
      refine.py             ← POST /reports/{id}/refine
    services/
      approval_gate.py      ← Gate trigger logic (pure function, no side effects)
      feedback_logger.py    ← Append every gate decision to logs/gate_decisions.jsonl
      refinement.py         ← Partial re-run: inject constraint, re-run Steps 5–8
    models/
      session.py            ← Session, Report Pydantic models
      gate.py               ← ApprovalGate, GateDecision, RefinementRequest
    db/
      store.py              ← JSON file store (sessions/{session_id}.json)

frontend/
  src/
    App.jsx                 ← State machine: brief → loading → report/gate → refine
    components/
      BriefInput.jsx        ← Textarea + submit (21st.dev component)
      Report.jsx            ← 9 accordion sections (shadcn Accordion)
      ConfidenceScore.jsx   ← Color-coded score bar + deductions
      GateAlert.jsx         ← Amber banner + approve/reject/refine buttons
      RefinementInput.jsx   ← Chat-style constraint update (21st.dev component)
    hooks/
      useReport.js          ← All API state: report, gate, loading, generate/decide/refine
    api/
      client.js             ← fetch wrapper, VITE_API_URL from .env
  .env                      ← VITE_API_URL=http://localhost:8000
  package.json
  vite.config.js
  tailwind.config.js
```

**Approval gate trigger conditions** (`approval_gate.py` — fires when ANY is true):
```
confidence_score < 60                              → plan needs review
any risk_register[].score == "CRITICAL"            → critical risk requires PM decision
project_viability.viability_status == "NOT_VIABLE" → impossible constraints
any open_questions[].urgency == "Before planning"  → anti-pattern detected
```
If none triggered → `fired: False` (auto-approved, no human action needed).

**Refinement loop — locked vs re-run:**
```
Steps 1–4  LOCKED  — extraction already done, brief didn't change
Steps 5–8b RE-RUN  — plan, tasks, risks, staffing, viability recalculated
```
Refinement message passes `previous_report` JSON + `feedback` string; agent updates only downstream sections.

**MVP persistence** — `sessions/{session_id}.json` (no database):
```json
{
  "session_id": "abc123",
  "reports": [{
    "report_id": "rpt_001",
    "report": { "...agent output..." },
    "gate": { "fired": true, "reasons": ["..."], "decision": null },
    "refinements": [{ "feedback": "cut timeline to 8 weeks", "report": {}, "gate": {} }]
  }]
}
```

**Local dev (two terminals):**
```bash
uvicorn backend.api.main:app --reload --port 8000   # backend
cd frontend && npm run dev                   # frontend → localhost:5180 (avoids :5173 clashes)
```

**Unchanged from Project 1:** `agent/main.py`, `agent/validator.py`, `prompts/`, `knowledge-base/`, all eval scripts.

### Project 3: Multi-Agent Orchestration (BA + PM pipeline)

> **Implementation status:** Project 3 is **specified** here for course progression; sub-agents, RAG, `drawio_generator.py`, Kroki, and orchestrator gates are **not** implemented in this repo yet.

**Goal:** Replace monolithic `_build_system_context()` with **RAG retrieval** per agent and split work across **specialized sub-agents**. The pipeline is grounded in a shared use-case model so plan, risks, and staffing stay internally consistent.

**Zeroth step — Use Case Agent (before Intake):**
The Use Case Agent is the first sub-agent. It reads raw requirements and produces a structured intermediate artifact consumed by every downstream agent.

**Diagram generation — two-step design (LLM for reasoning, Python for rendering):**
```
Step 1 — LLM produces structured use case data (what to draw):
{
  "system_boundary": "Employee Onboarding Portal",
  "actors": [
    { "id": "A1", "name": "New Hire",      "type": "primary"   },
    { "id": "A2", "name": "HR Team",       "type": "secondary" },
    { "id": "A3", "name": "IT Department", "type": "external"  }
  ],
  "use_cases": [
    { "id": "UC1", "name": "Complete paperwork",  "actors": ["A1"]       },
    { "id": "UC2", "name": "Provision IT access", "actors": ["A1", "A3"] },
    { "id": "UC3", "name": "Monitor progress",    "actors": ["A2"]       }
  ],
  "relationships": [
    { "type": "includes", "from": "UC1", "to": "UC4" }
  ]
}

Step 2 — drawio_generator.py converts structured data → valid draw.io XML (Python only):
  - Grid layout algorithm handles positioning (no overlaps)
  - Deterministic unique cell IDs — no LLM involvement
  - Correct draw.io style strings from templates
  Result: valid .drawio XML the PM can edit in app.diagrams.net (no install required)
```

**Diagram delivery:**
```
drawio_generator.py  →  .drawio XML file
      ↓
Kroki free API  →  POST diagram XML  →  PNG returned
      ↓
React report: inline PNG image + "Download .drawio" button
```

**Full agent pipeline (end-to-end):**
```
Raw requirements
      │
      ▼
[Use Case Agent]   → actors, use cases, draw.io XML, PNG → use_case_model.json
      │  ← Orchestrator gate: input quality LOW or anti-pattern detected?
      ▼
[Intake Agent]     → Steps 1–4 → structured_brief.json
                     (extraction grounded in named use cases)
      │  ← Orchestrator gate: confidence < 60 or >5 assumptions?
      ▼
[Planning Agent]   → Steps 5–6 → project_plan.json
                     (phases/milestones/tasks tied to use case IDs)
      │  ← Orchestrator gate: timeline HIGH RISK?
      ▼
[Risk Agent]       → Step 7 → risk_register.json
                     (risks tied to use cases and actors)
      │  ← Orchestrator gate: CRITICAL risks require PM decision?
      ▼
[Staffing Agent]   → Step 8 → staffing_plan.json
                     (roles matched to use-case complexity and load)
      │  ← Auto-validated by business rules (no human gate needed)
      ▼
[Synthesis Agent]  → consistency check (use case ↔ plan ↔ risks ↔ staffing)
      │  ← Orchestrator gate: cross-section contradictions found?
      ▼
Final integrated report
  ├── Use case diagram (editable .drawio + inline PNG)
  ├── Structured use case descriptions
  ├── Project plan (phases tied to use case IDs)
  ├── Risk register (risks tied to use cases)
  ├── Staffing plan (roles matched to use case complexity)
  └── All existing metadata (assumptions, confidence, viability)
```

**Approval gates in P3 — at every handoff, not just at the end:**
Each gate pauses only the affected agent. Downstream agents do not run until the gate clears. When the PM provides feedback, only the agent that owns the flagged section re-runs — not the full pipeline.

**Knowledge base and RAG:**
KB material moves to a vector store (Pinecone or Weaviate). Each agent retrieves only its relevant slice. `_build_system_context()` in `agent/main.py` is replaced with RAG retrieval — method signature unchanged, only the implementation changes.

**Orchestrator:**
Coordinates ordering, passes `use_case_model` and prior JSON between agents, handles retries, runs gate checks at each handoff, invokes Synthesis for a consistency pass before returning the final artifact.

**Agent count:** Six specialized LLM steps — **Use Case**, **Intake**, **Planning**, **Risk**, **Staffing**, **Synthesis** — replacing the single P1 agent while preserving the same 8-step reasoning semantics across the pipeline.