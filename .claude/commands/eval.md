# /eval

Safe eval workflow for PLANR. Always starts with the free replay path
and only escalates to generation (API cost) when explicitly needed.

---

## Before You Start — Check What's Cached

```bash
ls outputs/
```

If cached outputs exist for the current prompt version, start with Step A (free).
If nothing is cached, skip to Step B (costs tokens).

---

## Step A — Replay Cached Outputs (Free, Always Try First)

Scores cached outputs across all eval dimensions. No API calls.

```bash
make eval-replay
```

Or by dimension:
```bash
python scripts/run_eval.py --replay --dimension schema
python scripts/run_eval.py --replay --dimension rubric
python scripts/run_eval.py --replay --dimension edge
```

**Run this as many times as needed** — changing the validator, rubric logic,
or scoring expectations does not require regeneration.

---

## Step B — Generate Fresh Outputs ⚠️ Costs API Tokens

Only run this when:
- The active prompt version has changed (new `prompts/v*.txt`)
- No cached outputs exist for the current version
- You explicitly need fresh generation (consistency testing)

```bash
make eval-generate
```

Or for a single test case:
```bash
python scripts/run_eval.py --tc tc-01-perfect
```

**Model note:** `MODEL_HAIKU` is the default for iteration (cheaper).
Switch to `MODEL_SONNET` in `agent/main.py` for official eval runs and Demo Day outputs.

---

## Step C — Full Generate + Replay + Score

Runs both steps in sequence. Use for official eval runs only.

```bash
make eval-all
```

---

## Reading the Results

Every eval run prints a cost summary: API calls made, tokens used, estimated USD.
Scorecards are saved to `results/p1/eval/`.

**Pass targets:**

| Dimension | Target |
|-----------|--------|
| Schema pass rate | 100% |
| Rubric average | > 3.5 / 5 |
| Edge case pass rate | > 80% |
| Consistency variance | < 15 (same 10-point band across 3 runs on TC-01) |

---

## Checklist

- [ ] Checked `outputs/` for existing cached results
- [ ] Ran `eval-replay` first (free)
- [ ] Only ran `eval-generate` if the prompt version changed or cache is empty
- [ ] Reviewed cost summary after any generation run
- [ ] Results saved to `results/p1/eval/`
- [ ] If running for a prompt bump — record rubric delta in `prompts/PROMPT_CHANGELOG.md`
