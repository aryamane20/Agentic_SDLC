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

| Role | Allocation Range | Critical Path | Phase Pattern |
|------|-----------------|---------------|---------------|
| Product Manager | 10-15% of total hours | Yes | All phases |
| Solution Architect | 40-60% Phase 1, 10% ongoing | No | Front-loaded |
| Frontend Developer | 60-80% | Yes | Phases 2-4 |
| Backend Developer | 60-80% | Yes | Phases 2-4 |
| Full Stack Developer | 70-80% | Yes | Phases 2-4 |
| QA Engineer | Min 25% of dev hours | Yes | Phases 3-4 heavy |
| UX Designer | 40-60% Phases 1-2, 10% after | No | Front-loaded |
| Data Engineer | 60-80% | Yes | Phases 2-4 |
| DevOps / Platform Engineer | 20-30% early, 70-80% Phase 5 | No | Back-loaded |
| Integration Specialist | 60-80% Phases 1-3 | Yes | Front/mid-loaded |
| Data Analyst / BI Developer | 40-60% Phases 3-4 | No | Back-loaded |
| Security Engineer | 30-50% Phase 3, review in Phase 4 | No | Mid-loaded |

**Allocation rule (hard):** No role above 80% — PMBOK 9.2 resource leveling principle.
**PM oversight rule (hard):** PM must be 10-15% of total project hours — PMBOK 9.2.

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
  PM hours maximum:     500h × 15% = 75h
```

If the input specifies a developer-only team with no PM, flag the PM role as missing and include it in the staffing plan. Every project needs exactly one accountable owner.
