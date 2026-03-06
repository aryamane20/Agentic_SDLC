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
pm-digital-twin/
│
├── README.md                        ← You are here
├── .env.example                     ← Environment variables template
├── .gitignore
│
├── docs/                            ← All design documentation
│   ├── ARCHITECTURE.md              ← Full system design
│   ├── DESIGN_DECISIONS.md          ← Why we made each choice
│   ├── PRE_MORTEM.md                ← Predicted failure modes
│   └── EVALUATION_RUBRIC.md        ← How we score output quality
│
├── agent/                           ← The PM brain
│   ├── prompts/
│   │   ├── system_prompt_v1.md      ← Active system prompt
│   │   └── PROMPT_CHANGELOG.md      ← Version history of every change
│   └── schema/
│       └── output_schema.json       ← JSON contract for all outputs
│
├── knowledge-base/                  ← PM domain knowledge (inline for P1)
│   ├── templates/
│   │   ├── type-a-new-tool.md       ← New internal tool template
│   │   ├── type-c-data-pipeline.md  ← Data pipeline template
│   │   └── type-d-integration.md   ← System integration template
│   ├── risks/
│   │   └── risk-patterns.md         ← PMI-grounded risk catalog
│   └── staffing/
│       └── role-definitions.md      ← Role benchmarks and effort estimates
│
├── inputs/                          ← All test case inputs
│   └── test-cases/
│       ├── tc-01-perfect.txt        ← Complete requirements
│       ├── tc-02-good.txt           ← Most fields, minor gaps
│       ├── tc-03-medium.txt         ← Key fields, significant gaps
│       ├── tc-04-vague.txt          ← Goal only, nothing else
│       ├── tc-05-contradictory.txt  ← Impossible constraints
│       ├── tc-06-type-a.txt         ← New internal tool
│       ├── tc-07-type-c.txt         ← Data pipeline
│       ├── tc-08-type-d.txt         ← System integration
│       ├── tc-09-short-timeline.txt ← 2 weeks, complex project
│       └── tc-10-solo-team.txt      ← 1 person, large project
│
├── outputs/                         ← Auto-generated, gitignored except samples
│   └── samples/
│       └── tc-01-sample-output.json ← Reference output for TC-01
│
├── src/                             ← All source code
│   ├── main.py                      ← Entry point
│   ├── agent.py                     ← LLM call + prompt management
│   ├── parser.py                    ← JSON extraction + cleaning
│   ├── validator.py                 ← Schema validation
│   └── logger.py                    ← Structured execution logging
│
└── eval/                            ← Evaluation framework
    ├── run_eval.py                  ← Master eval runner
    ├── schema_validator.py          ← Dimension 1: correctness
    ├── consistency_test.py          ← Dimension 2: determinism
    ├── rubric_scorer.py             ← Dimension 3: reasoning quality
    ├── edge_case_runner.py          ← Dimension 4: edge cases
    └── results/
        └── eval_report_template.json
```

---

## How to Run

### Setup
```bash
git clone <your-repo>
cd pm-digital-twin
pip install -r requirements.txt
cp .env.example .env
# Add your API key to .env
```

### Run on a single input
```bash
python src/main.py --input inputs/test-cases/tc-01-perfect.txt
```

### Run full evaluation suite
```bash
python eval/run_eval.py --all
```

### Run specific test case
```bash
python src/main.py --input inputs/test-cases/tc-04-vague.txt --verbose
```

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
| Consistency | Same input = same output (5 runs) | Yes |
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

See `agent/prompts/PROMPT_CHANGELOG.md` for full history.
