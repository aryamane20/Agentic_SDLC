# P2 — pytest test files

All tests here are mocked — no API key or tokens needed.

Run the full P2 suite:
```bash
make test-p2
```

## Test files

| File | What it tests | Loads data from |
|------|--------------|-----------------|
| `test_input_guard.py` | Classify 17 intake fixtures — REFUSED / NEEDS_BRIEF / OK verdicts | `inputs/test-cases-p2/intake/` |
| `test_generate_input_guard.py` | Guard wired into POST /reports/generate — 422 on bad input, 200 on clean | Mocked PMAgent + store |
| `test_p2_gates_fixtures.py` | Gate fires correctly on frozen report JSON | `inputs/test-cases-p2/fixtures/gates/*.json` |
| `test_p2_refinement_replay.py` | Gate state is correct across a multi-round refine sequence | `inputs/test-cases-p2/fixtures/refinement/*/` |
| `test_api_approval_gate.py` | Gate trigger rules (confidence, CRITICAL risk, all reasons collected) | Inline fixtures |
| `test_hitl_flow.py` | Gate-as-warning model: generate → gate fires → refine still allowed | Mocked PMAgent + store |
| `test_p2_revision_conflict.py` | 409 on stale `expected_revision`; no disk write on conflict | Mocked store |
| `test_refinement_locked_sections.py` | Steps 1–4 are locked after refinement (deterministic merge) | Inline fixtures |
| `test_read_endpoints.py` | GET /reports and GET /gates — happy path + 404 | Mocked store |
| `test_user_isolation.py` | User A cannot see User B's sessions or reports | Real temp dir via `tmp_path` monkeypatch |
| `test_document_upload.py` | File upload — .txt, .md, .pdf, .docx, oversized, empty, wrong type | Inline bytes via TestClient |
| `test_validation_retry.py` | Generate retries up to 3 times on bad agent output; no infinite loop | Mocked PMAgent |
| `conftest.py` | Shared fixtures (`P2_FIXTURES` path helper) | `inputs/test-cases-p2/fixtures/` |

## Data locations

- **Intake guard fixtures:** `inputs/test-cases-p2/intake/*.txt` + `expectations.json`
- **Frozen gate fixtures:** `inputs/test-cases-p2/fixtures/gates/*.json`
- **Refinement snapshots:** `inputs/test-cases-p2/fixtures/refinement/*/`
- **P1 eval scorecards:** `results/p1/eval/` (from `scripts/run_eval.py`)
- **P2 live E2E logs:** `results/p2/e2e/`
