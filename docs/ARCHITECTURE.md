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
│   │  2. JSON Extraction (parser.py)                          │   │
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
**Lives in:** `prompts/v1.4_system.txt` (current active version)
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
  "pm_confidence_score": 0-100
}
```

### PM Confidence Score Calculation
```
Base score: 100

Deductions:
  -10 per UNKNOWN hard constraint
  -5 per HIGH risk_if_wrong assumption
  -15 if classification confidence is LOW
  -20 if contradictory constraints detected
  +0 floor (minimum score: 0)

Interpretation:
  80-100: High quality input, output reliable
  60-79:  Medium quality, review assumptions carefully
  40-59:  Low quality input, treat as draft only
  0-39:   Very low, human must validate everything
```

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

| Layer | Technology | Why |
|-------|-----------|-----|
| LLM | Claude (claude-haiku-4-5-20251001 dev / claude-sonnet-4-20250514 eval) | Consistent structured output |
| Language | Python 3.11+ | OpenHands compatible |
| Validation | jsonschema library | Schema enforcement |
| Logging | Python logging + JSON | Structured, parseable logs |
| Testing | pytest | Unit + integration tests |
| Version Control | Git | Prompt versioning + code |

---

## 7. Project Evolution Path

### Project 1: Single Agent
```
Input → System Prompt → LLM → Parser → Validator → Output
```
Everything in one agent. Knowledge base embedded in system prompt.

### Project 2: Add Approval Gates
```
Input → Agent → Output
                  │
                  ▼
         [Confidence Score < 60?]  →  PAUSE → Human Review → Approve/Reject
         [Critical Risk present?]  →  PAUSE → Human Review → Approve/Reject
                  │
                  ▼ (if approved)
                  
            Final Report
```

New components: `approval_gate.py`, `review_interface.py`, `feedback_logger.py`

### Project 3: Multi-Agent Orchestration
```
Input
  │
  ▼
[Orchestrator]
  ├── [Intake Agent]    → Steps 1-4 → structured_brief.json
  ├── [Planning Agent]  → Steps 5-6 → project_plan.json
  ├── [Risk Agent]      → Step 7    → risk_register.json
  └── [Staffing Agent]  → Step 8    → staffing_plan.json
        │
        ▼
  [Synthesis Agent]     → Consistency check → Final Report
```

Knowledge base extracted to vector store. Each agent queries only its section.
