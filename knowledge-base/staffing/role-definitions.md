# Staffing Benchmarks & Role Definitions
# Knowledge Base — PM Digital Twin
# Version: 1.0.0
#
# PURPOSE: Use during Step 8 (Staffing Plan) as baseline reference.
# These are benchmarks — real projects vary. Always adjust based on
# project-specific constraints (team size given, tech stack complexity,
# known skill gaps). Never let these override hard constraints in the input.
#
# WHEN TO UPDATE THIS FILE:
# - Eval run shows agent producing unrealistic hour estimates
# - New role types needed for emerging project patterns
# - Benchmarks diverge significantly from real-world feedback
# NOTE: The RULES (never exceed 80%, QA minimum 25%) live in the role
# (system_prompt). This file contains the DATA those rules apply to.
# ─────────────────────────────────────────────────────────────────────────────

---

## ROLE DEFINITIONS & ALLOCATION BENCHMARKS

| Role | Allocation Range | Critical Path | Phase Pattern | PMI Basis |
|------|-----------------|---------------|---------------|-----------|
| Product Manager | 10-15% of total hours | Yes | All phases | PMBOK 9.2 |
| Solution Architect | 40-60% Phase 1, 10% ongoing | No | Front-loaded | PMBOK 9.2 |
| Frontend Developer | 60-80% | Yes | Phases 2-4 | PMBOK 9.2 |
| Backend Developer | 60-80% | Yes | Phases 2-4 | PMBOK 9.2 |
| Full Stack Developer | 70-80% | Yes | Phases 2-4 | PMBOK 9.2 |
| QA Engineer | Min 25% of dev hours | Yes | Phases 3-4 heavy | PMBOK 8.2 |
| UX Designer | 40-60% Phases 1-2, 10% after | No | Front-loaded | PMBOK 9.2 |
| Data Engineer | 60-80% | Yes | Phases 2-4 | PMBOK 9.2 |
| DevOps / Platform Engineer | 20-30% early, 70-80% Phase 5 | No | Back-loaded | PMBOK 9.2 |
| Integration Specialist | 60-80% Phases 1-3 | Yes | Front/mid-loaded | PMBOK 9.2 |
| Data Analyst / BI Developer | 40-60% Phases 3-4 | No | Back-loaded | PMBOK 9.2 |
| Security Engineer | 30-50% Phase 3, review in Phase 4 | No | Mid-loaded | PMBOK 8.1 |

**Allocation rule (hard):** No role above 80% — PMBOK 9.2 resource leveling principle.
**PM oversight rule (hard):** PM must be 10-15% of total project hours — PMBOK 9.2.

---

## EFFORT ESTIMATION BENCHMARKS

*Baseline: 6 productive hours per working day (accounts for meetings, context switching).*
*Always add 15% schedule reserve on top of task estimates (PMBOK 6.5).*

### Development Tasks

| Task Type | Low Estimate | High Estimate | Notes |
|-----------|-------------|---------------|-------|
| Simple API endpoint | 4 hours | 8 hours | CRUD, no complex logic |
| Complex API endpoint | 8 hours | 16 hours | Business logic, validation, error handling |
| Frontend page (simple) | 4 hours | 8 hours | Static layout, minimal state |
| Frontend page (complex) | 8 hours | 24 hours | Forms, state management, API integration |
| Frontend component (reusable) | 4 hours | 12 hours | Depends on complexity |
| Database schema design | 8 hours | 24 hours | Simple to complex relationships |
| Database migration script | 4 hours | 16 hours | Data volume and complexity dependent |
| Third-party API integration | 8 hours | 32 hours | Sandbox to production, auth, error handling |
| Authentication system | 16 hours | 40 hours | SSO adds significant complexity |
| Data pipeline (single source) | 24 hours | 80 hours | Ingestion + transform + load + monitoring |
| ETL transformation rule | 4 hours | 16 hours | Simple mapping to complex logic |
| BI dashboard | 16 hours | 40 hours | Depends on number of visualizations |

### Testing Tasks

| Task Type | Estimate | PMI Basis |
|-----------|----------|-----------|
| Unit test suite | 30% of implementation time | PMBOK 8.2 |
| Integration test suite | 50% of implementation time | PMBOK 8.2 |
| End-to-end test suite | 20-30% of total dev time | PMBOK 8.2 |
| Performance/load testing | 16-32 hours | PMBOK 8.2 |
| Security/penetration testing | 24-40 hours (if in scope) | PMBOK 8.1 |
| UAT facilitation | 8-16 hours per round | PMBOK 8.3 |

### Non-Development Tasks

| Task Type | Estimate | Notes |
|-----------|----------|-------|
| Requirements document | 8-16 hours | Complexity dependent |
| Architecture document | 8-24 hours | System complexity dependent |
| API documentation | 4-8 hours per endpoint | |
| User documentation | 8-16 hours | |
| Code review | 15-20% of implementation time | Per team member |
| Deployment (simple) | 4-8 hours | Standard environment |
| Deployment (complex) | 8-24 hours | Multi-environment, migrations |
| Training session | 4-8 hours | Preparation + delivery |
| Project kickoff | 4-8 hours | Preparation + facilitation |

---

## QA STAFFING RULE (PMBOK 8.2)

**The 25% Rule:** QA effort must be at minimum 25% of total development effort.

```
Example calculation:
  Frontend dev total hours:   120h
  Backend dev total hours:    160h
  Total development hours:    280h

  Minimum QA hours:           280h × 25% = 70h
  QA Engineer at 60% for 8-week project: 8 weeks × 5 days × 6h × 60% = 144h
  → 144h > 70h minimum: PASSES
```

If input specifies a team without a QA role, always flag this as a staffing gap and include QA in the recommended staffing plan regardless.

---

## PM HOURS RULE (PMBOK 9.2)

**The 10-15% Rule:** PM oversight = 10-15% of total project hours.

```
Example calculation:
  Total project hours:   500h
  PM hours minimum:      500h × 10% = 50h
  PM hours maximum:      500h × 15% = 75h
```

If the input specifies a developer-only team with no PM, flag the PM role as missing and include it in the staffing plan. Every project needs exactly one accountable owner.

---

## SKILL REQUIREMENTS BY PROJECT TYPE

### Type A (New Internal Tool)
```
Frontend: React or Vue (current version), TypeScript, REST API consumption
Backend: Node.js or Python, REST API design, PostgreSQL or similar
QA: Manual testing, automated testing (Selenium/Playwright/Cypress), API testing
DevOps: CI/CD (GitHub Actions or similar), containerization basics
```

### Type C (Data Pipeline)
```
Data Engineer: Python, SQL, ETL tools (dbt, Airflow, or similar), cloud data platform (Snowflake/BigQuery/Redshift)
Backend: API development if serving data, Python preferred
QA/Data Analyst: SQL proficiency, data validation, dashboard tools (Tableau/Looker/Power BI)
```

### Type D (System Integration)
```
Backend: REST/GraphQL API design, authentication protocols (OAuth 2.0, SAML), message queues
Integration Specialist: Specific platform knowledge (SAP, Salesforce, Workday, etc.)
QA: API testing (Postman/Newman), integration test automation, load testing
```

### Type E (Migration)
```
Developers: Existing system knowledge required, migration tooling experience
Data Engineer: If data migration involved — ETL proficiency
DevOps: Infrastructure-as-code, cloud platform experience, zero-downtime deployment
QA: Regression testing, data validation, parallel run management
```

### Type F (Process Automation)
```
Backend: Workflow engines, event-driven architecture, audit logging
QA: Business rule validation, exception scenario testing
Business Analyst (optional): Process documentation, edge case identification
```
