---
name: planr-hitl
description: >
  PLANR Human-in-the-Loop (HITL) system reference. Use this skill whenever
  working on approval gates, gate decisions, refinement flow, the refine
  router, useReportWorkflow hook, gate-alert component, or any task touching
  the generate → review → approve/reject → refine loop. Also triggers for:
  adding new gate conditions, debugging 409 errors, extending the frontend
  workflow phases, or reviewing the HITL integration test suite.
---

# PLANR HITL — System Reference

This skill is the authoritative reference for the Human-in-the-Loop layer of
PLANR (Project 2). Read this before touching any gate, refinement, or workflow
code. It captures the state machine, API contract, frontend contract, known
quirks, key file locations, and open gaps.

---

## 1. What HITL Does (One Paragraph)

After the PM agent generates a plan, four conditions can make the plan too risky
to act on without review. When any condition is true, a **gate fires** — a
visible alert that shows exactly why the plan needs attention. The gate is an
**informational signal, not a workflow lock**: the PM can always refine with
feedback (their feedback IS their response to the gate concerns), or approve to
formally close the plan, or start over from scratch. The gate is re-evaluated on
every new report after refinement — if the PM's feedback addresses the root
cause, the gate clears automatically. This creates an audit trail of every human
approval while keeping the feedback loop frictionless.

---

## 2. Gate Trigger Conditions

All four conditions are evaluated by `evaluate_gate()` — a **pure function** in
`backend/api/services/approval_gate.py`. No I/O, no side effects.

| # | Condition | Field checked | Why it matters |
|---|-----------|---------------|----------------|
| 1 | PM confidence score < 60 | `pm_confidence_score.score` | Plan lacks maturity for execution |
| 2 | Any risk is CRITICAL | `risk_register[].score == "CRITICAL"` | Showstopper; PM must decide mitigation |
| 3 | Project is NOT_VIABLE | `project_viability.viability_status == "NOT_VIABLE"` | Constraints are impossible as stated |
| 4 | Open question urgency = "Before planning" **AND** no WBS exists | `open_questions[].urgency` + `project_plan.phases` | Decomposition was blocked |

**Condition 4 workaround (v1.6.2):** The agent sometimes mis-tags questions
"Before planning" even after outputting a full WBS. `_plan_has_decomposed_tasks()`
suppresses the gate for this case when ≥5 phases and ≥1 task exist. The real fix
belongs in a v1.7 prompt update with worked examples — not in the gate logic.

### GateState schema

```json
{
  "fired": true,
  "reasons": ["confidence_score < 60 — plan needs review"],
  "decision": null
}
```

`decision` is `null` (undecided), `"approve"`, or `"reject"`.

---

## 3. The HITL State Machine

```
generate()
    │
    ▼
[REVIEW] ←────────────────────────────────────────┐
    │                                               │
    ├─ gate.fired=false                             │
    │     ├─ refine(feedback) ──► [REFINING] ──────┤
    │     └─ approve() ──────────► [APPROVED]      │
    │                                               │
    └─ gate.fired=true                             │
          │                                         │
          ▼                                         │
    ⚠ Gate alert shown (reasons list)              │
          │                                         │
    PM has three options:                           │
          │                                         │
          ├─ refine(feedback) → [REFINING] ─────────┤
          │   (feedback addresses the gate concern)  │  ← gate re-evaluated on new report
          │                                         │
          ├─ approve() → [APPROVED]                 │
          │   (PM accepts the plan despite flags)   │
          │                                         │
          └─ startOver() → [IDLE]                   │
              (frontend resets; new session)
```

**Design principle:** The gate never blocks refinement. Submitting feedback
through a fired gate IS the human-in-the-loop action — the PM is acknowledging
the concern and addressing it. Approve is the only action that formally closes
the plan. There is no `reject()` — starting over (fresh brief) or refining
(corrective feedback) both serve that purpose more cleanly.

---

## 4. Backend API Contract

### Sessions
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sessions` | POST | Create session workspace |
| `/sessions` | GET | List session summaries |
| `/sessions/{id}` | GET | Load full session state |

### Reports
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/reports/generate` | POST | Run agent, save report, evaluate gate |
| `/reports/{id}` | GET | Fetch single report entry |
| `/reports/extract-document` | POST | Extract text from PDF/DOCX |

### Gates
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/gates/{report_id}` | GET | Fetch current gate state |
| `/gates/{report_id}/decision` | POST | Record approve/reject decision |

**Gate decision body:**
```json
{ "session_id": "ses_...", "decision": "approve" }
```
Valid `decision` values: `"approve"` | `"reject"`.

### Refinement
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/reports/{report_id}/refine` | POST | Re-run Steps 5–8 with feedback |

**Refine body:**
```json
{
  "session_id": "ses_...",
  "feedback": "Extend timeline by 2 weeks",
  "update_brief": false
}
```

`update_brief=true`: Only `project_understanding` is locked; `assumption_log`
may change (use when feedback introduces a new constraint, not just a plan tweak).

**Refine error — 409 Conflict:**
Gate fired and decision is null. Frontend must surface a clear message directing
the PM to approve or reject before refining.

---

## 5. Refinement Contract (Steps 1–4 Locked)

`run_refinement()` in `backend/api/services/refinement.py`:

1. Strips `project_understanding` and `assumption_log` from the prior report
   JSON before sending to the LLM (saves tokens)
2. Sends a 3-turn Messages API thread:
   - Turn 1 (user): original brief
   - Turn 2 (assistant): compact prior JSON with `cache_control: ephemeral`
   - Turn 3 (user): feedback + instruction to revise Steps 5–8
3. After the call, `merge_locked_sections_from_prior()` force-restores the
   locked sections from the prior report — they cannot drift
4. Calls `evaluate_gate()` on the merged result
5. Returns `{ report, gate, tokens_used, input_tokens, output_tokens }`

**The router (`refine.py`) must NOT call `evaluate_gate()` again.** It must use
`GateState.model_validate(out["gate"])` to reconstruct from the service result.
This was a bug (double evaluation) that has been fixed.

**Locked sections (default):** `project_understanding`, `assumption_log`, plus
classification metadata (`input_quality`, `project_type`, `classification_confidence`,
`sdlc_approach`, `sdlc_rationale`).

---

## 6. Key File Map

| Purpose | Path |
|---------|------|
| Gate trigger logic (pure function) | `backend/api/services/approval_gate.py` |
| Refinement orchestration | `backend/api/services/refinement.py` |
| Refine HTTP router | `backend/api/routers/refine.py` |
| Gate HTTP router | `backend/api/routers/gates.py` |
| Gate decision audit log | `backend/api/services/feedback_logger.py` → `logs/gate_decisions.jsonl` |
| Session JSON persistence | `backend/api/db/store.py` |
| Gate + refine Pydantic models | `backend/api/models/gate.py` |
| Session/report Pydantic models | `backend/api/models/session.py` |
| FastAPI app wiring | `backend/api/main.py` |
| Frontend workflow hook | `frontend/src/hooks/use-report-workflow.ts` |
| Frontend gate alert component | `frontend/src/components/plan/gate-alert.tsx` |
| Frontend workflow phases type | `frontend/src/types/plan.ts` — `WorkflowPhase` |
| Gate unit tests | `tests/test_api_approval_gate.py` |
| HITL integration tests | `tests/test_hitl_flow.py` |

---

## 7. Frontend Contract

### WorkflowPhase state machine

```
"IDLE" → generate() → "GENERATING" → "REVIEW"
"REVIEW" → refine() → "REFINING" → "REVIEW"
"REVIEW" → approve() → "APPROVED"
```

### useReportWorkflow — relevant exports

| Export | Type | Purpose |
|--------|------|---------|
| `phase` | `WorkflowPhase` | Current UI phase |
| `gate` | `GateDTO \| null` | Current gate state |
| `generate()` | function | Run agent, POST `/reports/generate` |
| `refine()` | function | Submit feedback, POST `/reports/{id}/refine` |
| `approve()` | function | Record approve, POST `/gates/{id}/decision` |

### GateDTO shape (frontend)

```typescript
type GateDTO = {
  fired: boolean
  reasons: string[]
  decision: "approve" | "reject" | null
}
```

### Frontend must enforce

When `gate.fired && gate.decision === null`:
- **Show `gate-alert.tsx`** with the reasons list and the Approve button
- **Refine remains enabled** — feedback IS the PM's response to the gate concerns
- The refine composer can show a contextual hint (e.g. "Address the gate concerns in your feedback") but must not disable send

When `gate.fired && gate.decision === "approve"`:
- Show "Plan approved" indicator; refine is still available for follow-up tweaks

When `gate.fired === false`:
- No alert; normal approve + refine flow

---

## 8. Known Gaps (Open Work)

### Gap 1 — No `reject()` in the frontend (intentional design decision)

`useReportWorkflow` exposes `approve()` but no `reject()`. This is deliberate:
the three PM actions after a gate fires are **approve** (close the plan formally),
**refine with feedback** (address the concern — this IS the rejection response),
or **start over** (fresh brief). A separate reject button would be a dead end —
you'd record reject, then still have to refine or start over anyway. The gate
is informational; feedback is the PM's corrective action.

The backend still accepts `decision: "reject"` via the API for future tooling
(audit scripts, reporting), but the frontend does not expose it.

### Gap 2 — No full lifecycle integration test (partial coverage added)

`tests/test_hitl_flow.py` covers the refine endpoint with mocked store and agent.
`tests/p2/test_read_endpoints.py` covers GET /reports and GET /gates.
`tests/p2/test_user_isolation.py` covers cross-user session/report isolation via real temp dir.
Still missing: a single test that runs the full lifecycle — create session → generate →
gate decision → refine → approve → re-fetch — against a live API without mocks. D4
(scripted E2E) is the manual substitute.

### Gap 4 — "Before planning" gate bypass is a workaround

Prompt v1.6.2 agents sometimes tag questions "Before planning" even when a full
WBS was output. The gate suppresses this when `_plan_has_decomposed_tasks()` is
true. Fix belongs in the v1.7 system prompt with explicit worked examples showing
when each urgency label should be used.

### Gap 5 — Auth / multi-user isolation

`deps.py` reads `x-planr-user-id` header, defaulting to `"anonymous"`. All
anonymous users share the same session namespace. Pre-production must add OAuth2
or similar before real multi-user deployment.

---

## 9. Audit Trail

Every gate decision is appended to `logs/gate_decisions.jsonl`:

```json
{
  "timestamp": "2026-04-05T10:23:00.123Z",
  "session_id": "ses_abc123",
  "report_id": "rpt_def456",
  "decision": "approve",
  "gate_fired": true,
  "reasons": ["confidence_score < 60 — plan needs review"]
}
```

This file is append-only. Never truncate it in production — it is the compliance
record of every human decision made in the system.

---

## 10. Adding a New Gate Condition

1. Add the check to `evaluate_gate()` in `backend/api/services/approval_gate.py`
   — return early with `fired=True, reasons=[...]` or continue accumulating
2. Add a unit test in `tests/test_api_approval_gate.py` — one test per condition,
   one test for the "not fired" counterpart
3. Update the HITL integration test in `tests/test_hitl_flow.py` if the new
   condition affects the 409 enforcement path
4. Update the `GateDTO` reasons display in `frontend/src/components/plan/gate-alert.tsx`
   if the reason string needs special formatting
5. Update this SKILL.md (Section 2, the trigger table)

---

## 11. Prompt Compliance Notes

The agent (prompt v1.6.2) has two known tendencies relevant to gate behavior:

- **Over-tagging "Before planning":** Annotates questions with "Before planning"
  urgency even after a full WBS was produced. Gate compensates via
  `_plan_has_decomposed_tasks()`. Do not remove this guard until v1.7 prompt is
  validated.
- **Confidence score variance:** Temperature=0 minimizes variance but does not
  eliminate it. `_enforce_hard_caps()` in `agent/main.py` clamps scores
  deterministically after parsing. The gate threshold (< 60) is set conservatively
  to account for residual variance.
