# P2 results

Use this directory for **end-to-end HITL / gate / refinement** run logs (manual or scripted).

Suggested layout:

- `e2e/` — one file per scenario run, e.g. `p2-scenario-a-happy-path-2026-04-07T123456Z.json`
- Each file should capture: brief id, raw gate state after generate, each refine request + response gate state, and whether the run ended in APPROVED or stopped early.

Do not commit secrets or full PHI-bearing briefs if you customize scenarios.
