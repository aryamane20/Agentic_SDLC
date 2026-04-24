# P1 — pytest test files

All tests here are mocked — no API key or tokens needed.

Run the full P1 suite:
```bash
make test-p1
```

## Test files

| File | What it tests |
|------|--------------|
| `test_happy_path.py` | Valid input produces expected output format |
| `test_edge_cases.py` | Malformed/empty/boundary inputs handled without crash |
| `test_retry.py` | API failure scenarios trigger retry logic |
| `test_validator_v162_rules.py` | v1.6.2 mechanical validator rules (urgency, QA ratio, staffing assumptions) |
| `test_validator_overallocation.py` | Staffing over-allocation warnings vs NOT_VIABLE status |
| `test_viability_critical_path_weeks.py` | Critical path duration uses working-day weeks (5 d/wk) |
| `test_pm_confidence_cap_after_normalize.py` | Confidence hard-cap survives validator normalize |

## Fixtures

Shared fixtures are in `tests/conftest.py` (auto-loaded by pytest for all subdirs):
- `mock_anthropic_client` — mocked Anthropic client, no real API calls
- `agent` — `PMAgent` with mocked client
- `runner` — `AgentRunner` wrapping the mocked agent
- `validator` — `SchemaValidator` instance
- `sample_test_cases` — loads `inputs/test-cases-p1/tc-*.txt`
