# Human-editable feedback for P2 E2E (`--mode file`)

Each scenario folder can contain **`e2e_feedback/round_01.json`**, **`round_02.json`**, …

Shape:

```json
{
  "feedback": "Your PM instructions to the refinement agent (required).",
  "update_brief": false,
  "label": "optional short name for the run log"
}
```

- **`feedback`** — same role as `refinement_rounds[].feedback` in `manifest.json`.
- **`update_brief`** — passed to `POST /reports/{id}/refine` (scenario B sometimes uses `true`).
- **`label`** — optional; appears in the E2E JSON log.

**Workflow**

1. Copy text from `manifest.json` into these files, or edit freely before a run.
2. Run: `python scripts/run_p2_e2e.py --scenario scenario-a-happy-path --mode file`

Default rounds in the repo mirror the manifests so **`--mode manifest`** and **`--mode file`** start aligned until you edit the JSON files.
