# P2 fixtures — frozen report JSON (inputs, not test code)

Used by **`tests/p2/test_p2_gates_fixtures.py`** and **`tests/p2/test_p2_refinement_replay.py`**.

- **`gates/`** — single snapshots for gate-only checks (`evaluate_gate`).
- **`refinement/`** — per-scenario timelines: `initial.json`, `after_round_01.json`, `after_round_02.json`, plus `replay_expectations.json`.

**Briefs** for generating real reports live next door: `../scenario-*/brief.txt` and `manifest.json`.

Replace these minimal JSON files with full `PMReport` exports from your agent/API when you want end-to-end fidelity.
