# /prompt-bump

Guided checklist for creating a new prompt version in PLANR.
Run this whenever a change to the system prompt is needed.

---

## Step 1 — Identify the current active version

Check `agent/main.py`:
```python
def __init__(self, prompt_version: str = "vX.Y", ...)
```
Note the current version. The new version will be `vX.Y+1` (or `vX+1.0` for major changes).

---

## Step 2 — Create the new prompt file (never edit existing)

```bash
cp prompts/v<current>_system.txt prompts/v<new>_system.txt
```

Make your changes to `prompts/v<new>_system.txt` only.
The old file must remain unchanged for replay reproducibility.

---

## Step 3 — Update the active version in code

In `agent/main.py`, update the default argument:
```python
def __init__(self, prompt_version: str = "v<new>", model: str = MODEL_HAIKU):
```

Do not change anything else at this stage.

---

## Step 4 — Run baseline eval (generate fresh outputs)

⚠️ This costs API tokens. Use MODEL_HAIKU for iteration, MODEL_SONNET for final eval.

```bash
make eval-generate
```

Minimum test cases to cover: **TC-01 through TC-05**.
Note the rubric scores from the output.

---

## Step 5 — Replay and score (free)

```bash
make eval-replay
```

Compare rubric scores against the previous version.
Target: rubric average **> 3.5 / 5**, schema pass rate **100%**.

---

## Step 6 — Update the changelog

Append to `prompts/PROMPT_CHANGELOG.md`:

```markdown
## v<new> — <date>
- What changed and why
- Rubric score delta: X.X → X.X (TC-01 through TC-05)
- Any edge cases affected
```

---

## Step 7 — Commit with the required format

```
prompt(v<new>): short description of change

- Bullet: what changed
- Bullet: why it changed
- Test cases run: TC-01 through TC-05; rubric X.X → X.X
```

Do not bundle prompt changes with code changes in the same commit.

---

## Step 8 — Archive if needed

If the old version is no longer needed for replay, move it to `prompts/archive/`.
Keep at minimum the previous two versions in the root `prompts/` directory.

---

## Checklist Summary

- [ ] New `prompts/v<new>_system.txt` created (old file untouched)
- [ ] `agent/main.py` default version updated
- [ ] `make eval-generate` run on TC-01 through TC-05
- [ ] `make eval-replay` scores reviewed and pass targets met
- [ ] `prompts/PROMPT_CHANGELOG.md` updated
- [ ] Commit message follows required format
- [ ] Old version archived if no longer needed for replay
