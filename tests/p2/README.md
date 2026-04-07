# P2 — pytest only (no data files here)

Test **scripts** for Human-in-the-loop / gates / refinement replay:

| File | Loads data from |
|------|-----------------|
| `test_p2_gates_fixtures.py` | `inputs/test-cases-p2/fixtures/gates/*.json` |
| `test_p2_refinement_replay.py` | `inputs/test-cases-p2/fixtures/refinement/*/` |
| `conftest.py` | `P2_FIXTURES` → same `inputs/.../fixtures` path |

**Inputs:** `inputs/test-cases-p2/` — briefs, manifests, and **all** JSON fixtures.  
**P1 eval scorecards:** `results/p1/eval/` (from `scripts/run_eval.py`).  
**P2 manual E2E logs:** `results/p2/e2e/`.

Run: `pytest tests/p2/ -v`
