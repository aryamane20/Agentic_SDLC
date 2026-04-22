# P2 — pytest test files

All tests here are mocked — no API key or tokens needed.

Run the full P2 suite:
```bash
make test-p2-baseline
```

## Test files

| File | What it tests | Loads data from |
|------|--------------|-----------------|
| `test_p2_gates_fixtures.py` | Gate fires correctly on frozen report JSON | `inputs/test-cases-p2/fixtures/gates/*.json` |
| `test_p2_refinement_replay.py` | Gate state is correct across a multi-round refine sequence | `inputs/test-cases-p2/fixtures/refinement/*/` |
| `test_read_endpoints.py` | GET /reports and GET /gates — happy path + 404 | Inline fixtures (mocked store) |
| `test_user_isolation.py` | User A cannot see User B's sessions or reports | Real temp dir via `tmp_path` monkeypatch |
| `test_document_upload.py` | File upload — .txt, .md, .pdf, .docx, oversized, empty, wrong type | Inline bytes via TestClient |
| `test_validation_retry.py` | Generate retries up to 3 times on bad agent output; no infinite loop | Mocked PMAgent |
| `conftest.py` | Shared fixtures | `P2_FIXTURES` → `inputs/.../fixtures` |

## Data locations

- **Frozen gate fixtures:** `inputs/test-cases-p2/fixtures/gates/*.json`
- **Refinement snapshots:** `inputs/test-cases-p2/fixtures/refinement/*/`
- **P1 eval scorecards:** `results/p1/eval/` (from `scripts/run_eval.py`)
- **P2 live E2E logs:** `results/p2/e2e/`
