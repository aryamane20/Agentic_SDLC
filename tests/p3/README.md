# P3 — pytest test files

All tests here are mocked — no API key or tokens needed.

Run the full P3 suite:
```bash
make test-p3
```

## Test files (to be added as each step is implemented)

| File | What it tests |
|------|--------------|
| `test_partial_schemas.py` | Pydantic model validation for all partial artifacts |
| `test_base_agent.py` | BaseAgent run/run_async, retry logic, cache_control blocks |
| `test_use_case_agent.py` | UseCaseAgent user message format, valid artifact detection |
| `test_intake_agent.py` | IntakeAgent extracts structured_brief correctly |
| `test_planning_agent.py` | PlanningAgent produces project_plan + use_case_task_mapping |
| `test_risk_agent.py` | RiskAgent produces risk_register, mandatory checklist |
| `test_staffing_agent.py` | StaffingAgent allocation caps, QA 25% rule, confidence score |
| `test_synthesis_agent.py` | SynthesisAgent consistency rules, final_report assembly |
| `test_orchestrator_pipeline.py` | Full pipeline happy path with mocked agents |
| `test_checkpoint_resume.py` | Gate fires → checkpoint loaded → resume from correct stage |
| `test_p3_refinement_routing.py` | Section → correct agents re-run |
| `test_drawio_generator.py` | JSON → valid draw.io XML, no LLM |

## Data locations

- **Test briefs:** `inputs/test-cases-p3/*.txt` (or reuse from `inputs/test-cases-p1/`)
- **Frozen agent fixtures:** `inputs/test-cases-p3/fixtures/{agent}/*.json`
  - Populated by running `scripts/test_p3_prompts.py` and saving outputs
- **Prompt test outputs:** `outputs/p3/agent-runs/` (gitignored)
- **Full pipeline outputs:** `outputs/p3/pipeline/` (gitignored)

## Prompt testing (uses real API — costs tokens)

```bash
# Test one agent against one brief
python scripts/test_p3_prompts.py --agent use_case --tc tc-01-perfect

# Test all agents in sequence against tc-01 (full pipeline)
python scripts/test_p3_prompts.py --all --tc tc-01-perfect

# Test all agents against tc-01, tc-02, tc-03
python scripts/test_p3_prompts.py --all --tc tc-01-perfect tc-02-good tc-03-medium

# Save outputs as fixtures (locks them for replay tests)
python scripts/test_p3_prompts.py --all --tc tc-01-perfect --save-fixtures
```
