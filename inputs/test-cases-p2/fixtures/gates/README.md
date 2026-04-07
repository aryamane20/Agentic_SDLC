# Gate fixtures (dimension 1)

Each file is a **report** dict (full PMReport or minimal — only keys used by `evaluate_gate` must be correct).

Naming hints:

- `clean_no_gate.json` — fired=False
- `low_confidence.json` — score under 60
- `critical_risk.json` — CRITICAL in risk_register
- `not_viable.json` — NOT_VIABLE
- `before_planning_no_wbs.json` — blocking open question without decomposed plan

Copy real failing reports when debugging prompts; redact PII.
