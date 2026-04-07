# Refinement replay fixtures (dimension 2)

**CI-stable** gate checks on **frozen** report snapshots (no API).

## Layout per scenario (mirrors `scenario-*` folder names under `inputs/test-cases-p2/`)

```
inputs/test-cases-p2/fixtures/refinement/<scenario_slug>/
  replay_expectations.json   ← { "initial": {"fired": bool}, "after_round_01": {...}, ... }
  initial.json               ← after generate (minimal or full PMReport)
  after_round_01.json        ← after first refine
  after_round_02.json        ← optional
```

Checked-in snapshots use **minimal** JSON (only fields `evaluate_gate` reads). You may **replace** them with full **`report`** exports from Langfuse, API, or `outputs/` when debugging real prompt regressions.

## Workflow

1. Live run: save `report` after generate and after each refine.
2. Overwrite `initial.json` / `after_round_*.json` or add a new slug.
3. Update `replay_expectations.json` so pytest asserts the intended gate progression.

Redact PHI/secrets before commit.
