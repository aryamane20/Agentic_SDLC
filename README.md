# PM Digital Twin — Project 1
### Course: Vibe Coding to Agent Engineering (Spring 2026)
### Student: Arya Mane | Role: Developer/PM

---

## What This Is

An AI agent that replicates the thinking process of a senior **Internal Product Project Manager**. Given any project requirements — vague or detailed — the agent runs an 8-step reasoning process grounded in PMI/PMBOK frameworks and produces an integrated output: project plan, risk register, and staffing plan.

This is **not** a form-filling tool. The agent is designed to think first, then produce — the same way a real PM does.

---

## Course Project Progression

This use case evolves across all three course projects:

| Project | Mode | What Changes |
|---------|------|-------------|
| **Project 1** (this repo) | Doing | Single agent, embedded knowledge, deterministic output |
| **Project 2** | Deciding | Add approval gates for high-risk outputs |
| **Project 3** | Delegating | Split into 4 specialized sub-agents with orchestration |

---

## Repository Structure

```
Agentic_SDLC/
│
├── README.md                        ← Architecture answers + project status
├── .gitignore                      ← Standard Python + logs exclusion
├── requirements.txt                ← All Python dependencies pinned
│
├── agent/                          ← Agent implementation code
│   ├── __init__.py
│   ├── main.py                     ← Entry point: runs the agent end-to-end
│   ├── runner.py                   ← run_with_retry(), run_with_validation()
│   ├── logger.py                   ← Structured run logger (writes to logs/)
│   ├── validator.py                ← Output schema validation using pydantic
│   └── viability_checker.py        ← Project viability assessment logic
│
├── prompts/                        ← Versioned prompt files (immutable once committed)
│   ├── README.md                   ← Prompt design decisions and version changelog
│   ├── PROMPT_CHANGELOG.md        ← Full version history
│   ├── v1.0_system.txt           ← Baseline prompt
│   ├── v1.1_system.txt           ← Reasoning completeness (SDLC, NFR, critical path)
│   ├── v1.2_system.txt           ← Output reliability (JSON skeleton, calibration)
│   ├── v1.3_system.txt           ← Production architecture (JSON-only, scratchpad)
│   ├── v1.4_system.txt           ← Haiku compatibility (Budget risk, priority caps)
│   ├── v1.5_system.txt           ← Structural trim + anti-patterns
│   └── archive/                   ← Intermediate prompt versions for reproducibility
│
├── schemas/                        ← Input/output schema definitions
│   ├── input_schema.py            ← Pydantic model for expected input
│   ├── output_schema.py           ← Pydantic model for expected output
│   └── output_schema.json         ← Generated JSON schema (from Pydantic)
│
├── tests/                          ← pytest test suite
│   ├── __init__.py
│   ├── conftest.py                ← pytest fixtures
│   ├── test_happy_path.py         ← Valid input → expected output
│   ├── test_edge_cases.py         ← Malformed/empty/boundary inputs
│   └── test_retry.py              ← Mock API failure → retry → success
│
├── logs/                           ← Run logs (gitignored except samples)
│   ├── .gitignore                 ← Ignore all run logs EXCEPT samples/
│   └── samples/
│       ├── sample_success.json     ← Representative successful run
│       └── sample_failure.json     ← Representative failure run
│
├── docs/                           ← Architecture doc, pre-mortem, design decisions
│   ├── ARCHITECTURE.md            ← 5 Architecture Questions answered
│   ├── PRE_MORTEM.md              ← Failure mode table (predicted)
│   └── EVALUATION_RUBRIC.md       ← 4-dimension eval results
│
├── scripts/                        ← Utility scripts
│   ├── run_eval.py                ← Runs agent on eval set, outputs scorecard
│   └── analyze_logs.py            ← Parses logs/ for latency, failure rate
│
├── knowledge-base/                 ← PM domain knowledge (inline for P1)
│   ├── templates/
│   │   └── project-type-templates.md ← All project type templates (A-F)
│   ├── risks/
│   │   └── risk-patterns.md      ← PMI-grounded risk catalog
│   └── staffing/
│       └── role-definitions.md    ← Role benchmarks and effort estimates
│
├── inputs/                         ← All test case inputs
│   └── test-cases/
│       ├── tc-01-perfect.txt      ← Complete requirements
│       ├── tc-02-good.txt         ← Most fields, minor gaps
│       ├── tc-03-medium.txt       ← Key fields, significant gaps
│       ├── tc-04-vague.txt        ← Goal only, nothing else
│       ├── tc-05-contradictory.txt ← Impossible constraints
│       ├── tc-06-type-a.txt       ← New internal tool
│       ├── tc-07-type-c.txt       ← Data pipeline
│       ├── tc-08-type-d.txt      ← System integration
│       ├── tc-09-short-timeline.txt ← 2 weeks, complex project
│       └── tc-10-solo-team.txt   ← 1 person, large project
│
└── outputs/                       ← Auto-generated, gitignored except samples
    └── samples/
        └── tc-01-sample_output.json ← Reference output for TC-01
```

---

## How to Run

### Setup
```bash
git clone <your-repo>
cd Agentic_SDLC
pip install -r requirements.txt
# Add your API key to .env (ANTHROPIC_API_KEY)
```

### Run full evaluation suite (live — calls API)
```bash
python scripts/run_eval.py --all
```

### Run specific test case
```bash
python scripts/run_eval.py --tc tc-01-perfect
```

### Run specific dimension
```bash
python scripts/run_eval.py --dimension schema --tc tc-01-perfect
```

### Cost-saving workflow (generate once, replay free)
```bash
# Step 1: Generate outputs for all test cases — 1 API call per TC
python scripts/run_eval.py --generate

# Step 2: Evaluate cached outputs — no API calls, $0 cost
python scripts/run_eval.py --replay --dimension schema
python scripts/run_eval.py --replay --dimension rubric
python scripts/run_eval.py --replay --dimension edge

# Re-run Step 2 unlimited times after changing validator, rubric logic, or expectations.
# Only re-run Step 1 when the prompt changes.
```

Every eval run prints a **cost summary** (API calls, tokens, estimated USD).
Outputs are cached in `outputs/{prompt-version}/` and versioned by prompt.

### Run unit tests
```bash
pytest tests/
```

Unit tests use a **mocked Anthropic client** — no API key or tokens needed.
They verify code correctness (JSON extraction, retry logic, schema validation, logging)
independently from prompt/output quality, which is covered by the eval suite above.

---

## The 8-Step PM Reasoning Process

Every input — no matter how vague — goes through this exact sequence:

```
1. EXTRACT        → What is being built, for whom, why
2. CLASSIFY       → Project type (A through F)
3. CONSTRAINTS    → Hard vs soft constraints
4. ASSUMPTIONS    → Log every gap with PMI basis
5. DECOMPOSE      → Phases → Milestones → Tasks
6. TASKS          → Specific, assignable, time-bounded
7. RISKS          → PMI Risk Management (PMBOK 11.2)
8. STAFFING       → PMI Resource Management (PMBOK 9.2)
```

---

## Evaluation Summary

| Dimension | What It Tests | Automated? |
|-----------|--------------|------------|
| Schema Validation | Output structure correctness | Yes |
| Consistency | Same input = same output (3 runs on TC-01) | Yes |
| Reasoning Quality | Rubric scored 1-5 per dimension | Semi-manual |
| Edge Cases | 10 test cases across input spectrum | Yes |
| PM Comparison | Agent vs manual PM output | Manual |

Target metrics:
- Schema pass rate: **100%**
- Consistency score variance: **< 5 points**
- Rubric average: **> 3.5 / 5**
- Edge case pass rate: **> 80%**

---

## Prompt Versioning

Every prompt change is committed to git with this format:
```
prompt(v2): tighten assumption log format

- Added PMI basis requirement to every assumption
- Changed risk_if_wrong to include consequence string
- Tested on TC-01 through TC-05, rubric improved 3.2→3.8
```

See `prompts/README.md` for full history.
