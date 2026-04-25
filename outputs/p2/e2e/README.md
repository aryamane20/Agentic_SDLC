# P2 end-to-end run logs

Place **JSON logs** from `scripts/run_p2_e2e.py` here (the script writes them automatically).

Each run file includes:

- `session_id`, `report_id`, `scenario`
- **generate** response summary (gate, token usage)
- **refine** steps (feedback source, gate after each round)
- optional **gate decision** if you used `--approve-at-end`

**Prerequisites**

1. Repository root on `PYTHONPATH` when starting the API (see root `README.md`).
2. `uvicorn backend.api.main:app --reload --port 8000` (from repo root).
3. `ANTHROPIC_API_KEY` set in the environment where **uvicorn** runs (the server calls the agent).

**Human-editable feedback** (copy/edit before a run):

- `inputs/test-cases-p2/scenario-*/e2e_feedback/round_01.json`, `round_02.json`, …

See `inputs/test-cases-p2/README.md` for the full P2 layout.
