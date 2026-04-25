# P1 eval scorecards

`python scripts/run_eval.py` (live generate) writes **timestamped JSON** here: dimensions, pass/fail, cost. Not used by CI; optional local history.

Command-line replay reads cached plans from **`outputs/{prompt_version}/`** (see `run_eval.py`).
