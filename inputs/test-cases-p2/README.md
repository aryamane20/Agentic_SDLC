# P2 — HITL / gate / refinement workflow (inputs)

Everything **P2 needs as input** lives under **`inputs/test-cases-p2/`**, separate from P1 **`inputs/test-cases-p1/`**.

| Kind | Path |
|------|------|
| **Briefs + refinement prompts** | `scenario-*/brief.txt`, `scenario-*/manifest.json` |
| **Frozen report JSON (gates + replay)** | **`fixtures/gates/`**, **`fixtures/refinement/<scenario-slug>/`** |

Pytest **code** only: **`tests/p2/*.py`** — it loads JSON from **`fixtures/`** here.

## Layout

Each scenario is a directory:

| Directory | Intent |
|-----------|--------|
| `scenario-a-happy-path/` | Gate should **not** fire — clean REVIEW → approve path |
| `scenario-b-low-confidence/` | Gate fires on **confidence under 60** — exercise GateAlert + refine loop |
| `scenario-c-critical-risk/` | Gate fires on **CRITICAL** risk — PM must consciously approve or refine |

Files:

- `brief.txt` — paste into PLANR (or pass as agent input).
- `manifest.json` — metadata, **two** human-style refinement messages, soft expectations (LLM variance applies).

See **`fixtures/README.md`** for gate and refinement JSON snapshots used by CI.

## Running (when you are ready)

Do **not** run automatically as part of CI without mocks — these calls cost tokens.

1. Generate from `brief.txt` (agent or API).
2. Run `evaluate_gate(report)` (or observe API `gate` in response).
3. If gate fired: POST refine with `manifest.json` — use `refinement_rounds[].feedback` in order.
4. Re-check gate after each refinement (loop until approve or policy cap).

Write logs under `results/p2/e2e/` when you run (JSON or Markdown run log).

## Relation to P1

- **P1:** `inputs/test-cases-p1/tc-*.txt` + `scripts/run_eval.py` — report cache `outputs/{prompt_version}/`, scorecards **`results/p1/eval/`**.
- **P2:** this directory (`briefs` + **`fixtures/`** JSON) + `tests/p2/` — manual logs optional under **`results/p2/e2e/`**.
