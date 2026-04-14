# Graph Report - /Users/aryamane/Desktop/Agentic_SDLC  (2026-04-12)

## Corpus Check
- 125 files · ~100,099 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 807 nodes · 1195 edges · 86 communities detected
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 253 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_P2 Test Fixtures & Helpers|P2 Test Fixtures & Helpers]]
- [[_COMMUNITY_Gate Evaluation Logic|Gate Evaluation Logic]]
- [[_COMMUNITY_P3 Multi-Agent & Project Types|P3 Multi-Agent & Project Types]]
- [[_COMMUNITY_Prompt Versions & PM Reasoning|Prompt Versions & PM Reasoning]]
- [[_COMMUNITY_E2E Testing & Gate Fixtures|E2E Testing & Gate Fixtures]]
- [[_COMMUNITY_Output Schema & Validation|Output Schema & Validation]]
- [[_COMMUNITY_Evaluation Pipeline|Evaluation Pipeline]]
- [[_COMMUNITY_Edge Case & Boundary Tests|Edge Case & Boundary Tests]]
- [[_COMMUNITY_Input Schema & Pydantic Models|Input Schema & Pydantic Models]]
- [[_COMMUNITY_Business Rules Validator|Business Rules Validator]]
- [[_COMMUNITY_Viability & Critical Path|Viability & Critical Path]]
- [[_COMMUNITY_PMAgent Core Methods|PMAgent Core Methods]]
- [[_COMMUNITY_Retry & Failure Tests|Retry & Failure Tests]]
- [[_COMMUNITY_P2 Backend Architecture|P2 Backend Architecture]]
- [[_COMMUNITY_Happy Path Unit Tests|Happy Path Unit Tests]]
- [[_COMMUNITY_Interactive Graph UI|Interactive Graph UI]]
- [[_COMMUNITY_Session Persistence Layer|Session Persistence Layer]]
- [[_COMMUNITY_Staffing & Overallocation|Staffing & Overallocation]]
- [[_COMMUNITY_Gate Rule Unit Tests|Gate Rule Unit Tests]]
- [[_COMMUNITY_Log Analytics|Log Analytics]]
- [[_COMMUNITY_E2E Feedback Runner|E2E Feedback Runner]]
- [[_COMMUNITY_Plan Report View|Plan Report View]]
- [[_COMMUNITY_Report Diff Utilities|Report Diff Utilities]]
- [[_COMMUNITY_Refinement Lock Tests|Refinement Lock Tests]]
- [[_COMMUNITY_Plan Display Formatting|Plan Display Formatting]]
- [[_COMMUNITY_Gate Fixture Tests|Gate Fixture Tests]]
- [[_COMMUNITY_Report Workflow Hook|Report Workflow Hook]]
- [[_COMMUNITY_Session Hydration|Session Hydration]]
- [[_COMMUNITY_User & API Utils|User & API Utils]]
- [[_COMMUNITY_Plan Page & Refinement UI|Plan Page & Refinement UI]]
- [[_COMMUNITY_Confidence Cap Tests|Confidence Cap Tests]]
- [[_COMMUNITY_Refinement Replay Tests|Refinement Replay Tests]]
- [[_COMMUNITY_Request Dependencies|Request Dependencies]]
- [[_COMMUNITY_Scroll Cue UI|Scroll Cue UI]]
- [[_COMMUNITY_Studio Thread UI|Studio Thread UI]]
- [[_COMMUNITY_Studio Magic Card|Studio Magic Card]]
- [[_COMMUNITY_PRD Upload|PRD Upload]]
- [[_COMMUNITY_FastAPI App Package|FastAPI App Package]]
- [[_COMMUNITY_Gate Decision Logger|Gate Decision Logger]]
- [[_COMMUNITY_P2 Scenario Runner|P2 Scenario Runner]]
- [[_COMMUNITY_Test & Eval Philosophy|Test & Eval Philosophy]]
- [[_COMMUNITY_Frontend UI Components|Frontend UI Components]]
- [[_COMMUNITY_Prompt Versioning Rules|Prompt Versioning Rules]]
- [[_COMMUNITY_Data Pipeline Test Case|Data Pipeline Test Case]]
- [[_COMMUNITY_App Root|App Root]]
- [[_COMMUNITY_Card Curtain Reveal|Card Curtain Reveal]]
- [[_COMMUNITY_Studio Shine Border|Studio Shine Border]]
- [[_COMMUNITY_Plan Sidebar|Plan Sidebar]]
- [[_COMMUNITY_Plan Working Loader|Plan Working Loader]]
- [[_COMMUNITY_Plan Refine Exchange|Plan Refine Exchange]]
- [[_COMMUNITY_Reduced Motion Hook|Reduced Motion Hook]]
- [[_COMMUNITY_Thread Preview|Thread Preview]]
- [[_COMMUNITY_UI Utilities|UI Utilities]]
- [[_COMMUNITY_Tech Stack & Langfuse|Tech Stack & Langfuse]]
- [[_COMMUNITY_TC-02 Customer Dashboard|TC-02 Customer Dashboard]]
- [[_COMMUNITY_Vite Build Tool|Vite Build Tool]]
- [[_COMMUNITY_Tailwind Config|Tailwind Config]]
- [[_COMMUNITY_Vite Config|Vite Config]]
- [[_COMMUNITY_PostCSS Config|PostCSS Config]]
- [[_COMMUNITY_App Entry Point|App Entry Point]]
- [[_COMMUNITY_Vite Env Types|Vite Env Types]]
- [[_COMMUNITY_Plan Types|Plan Types]]
- [[_COMMUNITY_Button Component|Button Component]]
- [[_COMMUNITY_Floating Composer|Floating Composer]]
- [[_COMMUNITY_Gate Alert Component|Gate Alert Component]]
- [[_COMMUNITY_Landing Page|Landing Page]]
- [[_COMMUNITY_Backend Init|Backend Init]]
- [[_COMMUNITY_Backend Init|Backend Init]]
- [[_COMMUNITY_Backend Init|Backend Init]]
- [[_COMMUNITY_Backend Init|Backend Init]]
- [[_COMMUNITY_Backend Init|Backend Init]]
- [[_COMMUNITY_Backend Init|Backend Init]]
- [[_COMMUNITY_Agent Run Method|Agent Run Method]]
- [[_COMMUNITY_Multi-Turn Messages API|Multi-Turn Messages API]]
- [[_COMMUNITY_Jsonschema Dependency|Jsonschema Dependency]]
- [[_COMMUNITY_Dotenv Dependency|Dotenv Dependency]]
- [[_COMMUNITY_PyPDF Dependency|PyPDF Dependency]]
- [[_COMMUNITY_Python-Docx Dependency|Python-Docx Dependency]]
- [[_COMMUNITY_Input Schema File|Input Schema File]]
- [[_COMMUNITY_Eval Script|Eval Script]]
- [[_COMMUNITY_Project Type E Migration|Project Type E Migration]]
- [[_COMMUNITY_Project Type F Automation|Project Type F Automation]]
- [[_COMMUNITY_P2 E2E Run Logs|P2 E2E Run Logs]]
- [[_COMMUNITY_E2E Log Format|E2E Log Format]]
- [[_COMMUNITY_P1 Eval Scorecard|P1 Eval Scorecard]]
- [[_COMMUNITY_TC-03 API Gateway|TC-03 API Gateway]]

## God Nodes (most connected - your core abstractions)
1. `SchemaValidator` - 62 edges
2. `PMAgent` - 49 edges
3. `AgentRunner` - 29 edges
4. `GateState` - 26 edges
5. `PMReportLogger` - 22 edges
6. `SessionState` - 19 edges
7. `TestEdgeCases` - 17 edges
8. `PMReport` - 16 edges
9. `_five_phases_one_task()` - 13 edges
10. `ReportEntry` - 13 edges

## Surprising Connections (you probably didn't know these)
- `P3 RAG Retrieval Per Sub-Agent` --semantically_similar_to--> `Knowledge Base Layer - Domain Knowledge`  [INFERRED] [semantically similar]
  docs/ARCHITECTURE.md → CLAUDE.md
- `Mechanical Confidence Calculation Rule Reproducibility` --semantically_similar_to--> `Dimension 2 Consistency Testing`  [INFERRED] [semantically similar]
  prompts/v1.6_system.txt → docs/EVALUATION_RUBRIC.md
- `anthropic Python Package Dependency` --references--> `agent/main.py Entry Point`  [INFERRED]
  requirements.txt → README.md
- `HIPAA Compliance Requirement` --conceptually_related_to--> `Step 7: Risk Identification (PMI PMBOK 11.2)`  [INFERRED]
  inputs/test-cases-p2/scenario-c-critical-risk/brief.txt → prompts/v1.0_system.txt
- `EPIC Custom Connector Integration Risk (Unfinished Design)` --conceptually_related_to--> `Step 7: Risk Identification (PMI PMBOK 11.2)`  [INFERRED]
  inputs/test-cases-p2/scenario-c-critical-risk/brief.txt → prompts/v1.0_system.txt

## Hyperedges (group relationships)
- **Two-Layer Brain: Role Prompt + KB + Runtime Compiler** — claude_role_layer, claude_knowledge_layer, claude_build_system_context [EXTRACTED 0.95]
- **P2 HITL Approval Gate and Refinement Loop** — readme_backend_approval_gate, readme_backend_refinement, arch_p2_refinement_loop, arch_p2_approval_gates [EXTRACTED 0.95]
- **8-Step PM Reasoning Pipeline Steps 1-8** — arch_step1_extract, arch_step2_classify, arch_step3_constraints, arch_step4_assumptions, arch_step5_decompose, arch_step6_tasks, arch_step7_risks, arch_step8_staffing [EXTRACTED 1.00]
- **Prompt Version Evolution Chain (v1.0 through v1.6.2)** — v10_system_prompt, v11_system_prompt, v12_system_prompt, v13_system_prompt, v14_system_prompt, v15_system_prompt, v161_system_prompt, v162_system_prompt [EXTRACTED 1.00]
- **P2 Gate Test Scenarios (Happy Path, Low Confidence, Critical Risk)** — scenario_a_happy_path, scenario_b_low_confidence, scenario_c_critical_risk, gate_alert_mechanism [EXTRACTED 1.00]
- **Scenario C Risk Cluster (HIPAA + EPIC + Deadline + Understaffed)** — hipaa_compliance_req, epic_integration_risk, fixed_public_deadline, understaffed_team [EXTRACTED 0.95]
- **P2 Scenarios Drive Gate and Refinement Fixture Tests** — scenario_a_brief, scenario_b_brief, fixtures_readme, test_p2_gates_fixtures, test_p2_refinement_replay [INFERRED 0.85]
- **P1 Edge Case Test Cases with Impossible or High-Risk Constraints** — tc04_vague, tc05_contradictory, tc09_short_timeline, tc10_solo_team [INFERRED 0.80]
- **Refinement Snapshot Lifecycle: Initial to After Rounds** — refinement_initial_json, refinement_after_round_01, refinement_replay_expectations, test_p2_refinement_replay [EXTRACTED 0.90]

## Communities

### Community 0 - "P2 Test Fixtures & Helpers"
Cohesion: 0.04
Nodes (83): agent(), load_report_fixture(), logger(), mock_anthropic_client(), mock_api_failure(), Shared helpers for P2 fixture-based tests., Load a JSON report from inputs/test-cases-p2/fixtures/{parts...}., Mock Anthropic client for testing without API calls. (+75 more)

### Community 1 - "Gate Evaluation Logic"
Cohesion: 0.06
Nodes (52): _confidence_score(), evaluate_gate(), _plan_has_decomposed_tasks(), Approval gate triggers — pure functions, no I/O. See docs/ARCHITECTURE.md § Proj, True when the report already contains a populated WBS (5 phases typical, ≥1 task, GateDecisionRequest, GateState, GenerateReportRequest (+44 more)

### Community 2 - "P3 Multi-Agent & Project Types"
Cohesion: 0.04
Nodes (63): P3 drawio_generator.py Diagram Tool, P3 Kroki Free API Diagram Rendering, P3 Orchestrator Multi-Agent Coordinator, P3 RAG Retrieval Per Sub-Agent, P3 Use Case Agent - First Sub-Agent, Project Type A - New Internal Tool, Project Type B - Enhancement, Project Type C - Data Pipeline (+55 more)

### Community 3 - "Prompt Versions & PM Reasoning"
Cohesion: 0.07
Nodes (49): Anti-Pattern Check (Solution Smuggling, Feature Factory, Stakeholder Driven), Archived System Prompt v1.0.0, Archived System Prompt v1.1.0, Archived System Prompt v1.2.0, Archived System Prompt v1.6.0, 8-Step PM Reasoning Process, EPIC Custom Connector Integration Risk (Unfinished Design), Fixed Public Launch Deadline (2026-05-15, Board Announced) (+41 more)

### Community 4 - "E2E Testing & Gate Fixtures"
Cohesion: 0.05
Nodes (41): P2 E2E Feedback README, E2E Feedback Round JSON Shape, run_p2_e2e.py Script, evaluate_gate Function, Clean No Gate Fixture, Critical Risk Gate Fixture, Low Confidence Gate Fixture, Not Viable Gate Fixture (+33 more)

### Community 5 - "Output Schema & Validation"
Cohesion: 0.1
Nodes (33): PMReport, Complete PM Digital Twin report output model., _assumption_claims_stakeholder_or_scope_approval_complete(), _assumption_what_restates_brief_constraint(), _assumptions_mention_class(), _best_qa_ratio_risk_score(), _brief_mentions_expansion_class(), _brief_segments() (+25 more)

### Community 6 - "Evaluation Pipeline"
Cohesion: 0.07
Nodes (35): Output Pipeline - Extract JSON to Report, Output Schema Structure PMReport, PM Digital Twin System Overview, Dimension 1 Schema Validation, Dimension 2 Consistency Testing, Dimension 3 Reasoning Quality Rubric, Dimension 4 Edge Case Handling, Dimension 5 Real PM Comparison Manual (+27 more)

### Community 7 - "Edge Case & Boundary Tests"
Cohesion: 0.06
Nodes (18): Edge case tests for PM Digital Twin agent. Malformed/empty/boundary inputs shoul, JSON extractor should handle malformed JSON., Test edge cases and boundary conditions., Logger should handle reports with missing fields., Logger should handle None values in report., Agent should handle empty input gracefully., Validator should handle reports with missing fields., Validator should handle empty arrays. (+10 more)

### Community 8 - "Input Schema & Pydantic Models"
Cohesion: 0.12
Nodes (32): BaseModel, Enum, PMInput, Input Schema - Pydantic models for PM Digital Twin input validation., Input schema for PM Digital Twin agent.     Accepts raw project requirements tex, Assumption, AssumptionSource, CriticalPathSummary (+24 more)

### Community 9 - "Business Rules Validator"
Cohesion: 0.12
Nodes (15): _assumption_row(), _five_phases_no_tasks(), _five_phases_one_task(), _minimal_risks(), v1.6.2 mechanical validator rules: urgency consistency, QA ratio risk, staffing, WHAT must not echo a sentence already in project_understanding (known fact)., TestAssumptionRestatesBriefConstraint, TestBeforePlanningUrgencyConsistency (+7 more)

### Community 10 - "Viability & Critical Path"
Cohesion: 0.1
Nodes (17): Viability checker: critical path duration uses working-day weeks (5 d/wk)., check_viability(), InputConstraints, PM Digital Twin — Viability Checker Handles conditional viability checks based o, Extract budget and deadline from raw input text.                  Key challenge:, Extracted constraints from project requirements input., Extract estimated total cost from the report., Extract critical path duration in weeks from report. (+9 more)

### Community 11 - "PMAgent Core Methods"
Cohesion: 0.12
Nodes (11): PM Digital Twin — Agent Core Handles: prompt loading, knowledge base compilation, Deterministic hash of (prompt_version, model, temperature, input)., UTC wall time as ISO-8601 with Z suffix (avoids deprecated datetime.utcnow())., Wraps raw input with instructions to trigger 8-step reasoning., Post-processing safety net: mechanically enforce hard cap rules         that the, Extract the JSON object from the LLM's response.         The LLM produces a huma, Attempt to fix truncated JSON by adding missing closing braces., # NOTE: This API key only has access to claude-sonnet-4. Both constants (+3 more)

### Community 12 - "Retry & Failure Tests"
Cohesion: 0.1
Nodes (11): Retry tests for PM Digital Twin agent. Mock API failure scenarios should trigger, Test retry logic and failure handling., Runner should not exceed max_retries., Invalid output should trigger another agent run (cache busted on retry)., Runner should retry on API failure., validate_output=False skips schema check — run still succeeds., Runner should exhaust all retries on persistent failure., Delay = retry_delay * attempt (linear, not exponential). (+3 more)

### Community 13 - "P2 Backend Architecture"
Cohesion: 0.11
Nodes (19): P2 Approval Gate Trigger Conditions, P2 MVP Session JSON Persistence, P2 Refinement Loop Steps 1-4 Lock, FastAPI Backend Dependency, Uvicorn ASGI Server Dependency, Rationale: JSON File Store as Zero-Setup MVP Persistence, 8-Step PM Reasoning Process, backend/api FastAPI Application (+11 more)

### Community 14 - "Happy Path Unit Tests"
Cohesion: 0.12
Nodes (9): Happy path tests for PM Digital Twin agent. Valid input should produce expected, Test valid inputs produce expected output format., Agent run should return a dict with expected keys., Agent should parse JSON from LLM response., Runner should succeed on first try with valid input., Runner with validation should pass for valid output., Logger should log reports without error., Validator should pass for valid report. (+1 more)

### Community 15 - "Interactive Graph UI"
Cohesion: 0.23
Nodes (7): animate(), generateRandomPos(), handleMouseDown(), handleMouseMove(), nextWord(), Particle, toBitmapCoords()

### Community 16 - "Session Persistence Layer"
Cohesion: 0.44
Nodes (10): ensure_sessions_dir(), find_report_session(), _legacy_flat_path(), list_session_summaries(), load_session(), _normalize_user(), save_session(), _session_path() (+2 more)

### Community 17 - "Staffing & Overallocation"
Cohesion: 0.36
Nodes (6): _five_valid_phases(), _minimal_report_for_business_rules(), _overallocation_warnings(), Staffing over-allocation warnings vs project viability (NOT_VIABLE)., Enough structure for _check_business_rules without full Pydantic path., TestOverallocationNotViable

### Community 18 - "Gate Rule Unit Tests"
Cohesion: 0.22
Nodes (3): Unit tests for Project 2 approval gate rules (no HTTP)., Mis-tagged 'Before planning' must not block if WBS is present (v16.2 rubric alig, test_gate_does_not_fire_before_planning_when_plan_already_decomposed()

### Community 19 - "Log Analytics"
Cohesion: 0.31
Nodes (8): analyze_runs(), generate_report(), main(), parse_log_file(), Log Analyzer for PM Digital Twin Parses logs/runs/ for latency, failure rate, an, Generate a human-readable report from statistics., Parse a JSONL log file and return list of log entries., Analyze all run logs in the logs directory.

### Community 20 - "E2E Feedback Runner"
Cohesion: 0.43
Nodes (7): _find_scenario(), _iter_feedbacks(), _load_round_feedback(), main(), Returns list of (feedback, label_for_log, update_brief, source_note)., _request_json(), _utc_iso()

### Community 21 - "Plan Report View"
Cohesion: 0.33
Nodes (0): 

### Community 22 - "Report Diff Utilities"
Cohesion: 0.6
Nodes (5): computeReportDiff(), confidence(), confidenceInterpretation(), riskCount(), weeks()

### Community 23 - "Refinement Lock Tests"
Cohesion: 0.33
Nodes (1): Steps 1–4 merge after refinement — deterministic lock without live LLM.

### Community 24 - "Plan Display Formatting"
Cohesion: 0.5
Nodes (2): getMetadataObject(), getPmConfidence()

### Community 25 - "Gate Fixture Tests"
Cohesion: 0.4
Nodes (3): _gate_cases(), Dimension 1 — gate evaluation on file-backed report JSON (no API)., id, expect_fired, reason_substr (optional matcher on reasons, lower-case contain

### Community 26 - "Report Workflow Hook"
Cohesion: 0.5
Nodes (0): 

### Community 27 - "Session Hydration"
Cohesion: 0.67
Nodes (2): buildThreadFromReportEntry(), rid()

### Community 28 - "User & API Utils"
Cohesion: 0.83
Nodes (3): getPlanrUserId(), planrApiFetch(), randomId()

### Community 29 - "Plan Page & Refinement UI"
Cohesion: 0.5
Nodes (0): 

### Community 30 - "Confidence Cap Tests"
Cohesion: 0.83
Nodes (3): _report_pm_cap_fixture(), test_cap_drops_breakdown_normalize_cannot_restore_higher_score(), test_second_enforce_after_normalize_reapplies_cap_when_breakdown_present()

### Community 31 - "Refinement Replay Tests"
Cohesion: 0.5
Nodes (1): Dimension 2 — refinement replay: gate state on frozen JSON snapshots.  These JSO

### Community 32 - "Request Dependencies"
Cohesion: 0.5
Nodes (3): planr_user_id(), Request-scoped dependencies (e.g. per-browser plan namespace)., Isolates JSON sessions on disk per caller. The web app sends a stable UUID from

### Community 33 - "Scroll Cue UI"
Cohesion: 0.67
Nodes (0): 

### Community 34 - "Studio Thread UI"
Cohesion: 0.67
Nodes (0): 

### Community 35 - "Studio Magic Card"
Cohesion: 0.67
Nodes (0): 

### Community 36 - "PRD Upload"
Cohesion: 1.0
Nodes (2): extractPrdText(), readErrorBody()

### Community 37 - "FastAPI App Package"
Cohesion: 0.67
Nodes (1): FastAPI application package (routers, services, models, persistence).

### Community 38 - "Gate Decision Logger"
Cohesion: 0.67
Nodes (1): Append gate decisions to logs/gate_decisions.jsonl.

### Community 39 - "P2 Scenario Runner"
Cohesion: 1.0
Nodes (2): _load_manifests(), main()

### Community 40 - "Test & Eval Philosophy"
Cohesion: 0.67
Nodes (3): Test Philosophy - Unit vs Eval Separation, Rationale: Replay Eval First to Avoid API Token Cost, pytest Python Package Dependency

### Community 41 - "Frontend UI Components"
Cohesion: 0.67
Nodes (3): Particle Text Effect Component, Frontend Vite React TypeScript Stack, shadcn/ui Component Pattern

### Community 42 - "Prompt Versioning Rules"
Cohesion: 0.67
Nodes (3): Prompt Versioning Rules, Rubric Score Tracking Per Prompt Version, v1.6.1 Full Eval Results - D1-D4 All Pass

### Community 43 - "Data Pipeline Test Case"
Cohesion: 0.67
Nodes (3): Looker BI Dashboard, Snowflake Data Warehouse, TC-07 Type C Data Pipeline Marketing Analytics

### Community 44 - "App Root"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Card Curtain Reveal"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Studio Shine Border"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Plan Sidebar"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Plan Working Loader"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Plan Refine Exchange"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Reduced Motion Hook"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Thread Preview"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "UI Utilities"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Tech Stack & Langfuse"
Cohesion: 1.0
Nodes (2): Technology Stack Table, langfuse Python Package Dependency

### Community 54 - "TC-02 Customer Dashboard"
Cohesion: 1.0
Nodes (2): TC-02 Good Input Customer Dashboard Enhancement, PagerDuty Alerting Integration

### Community 55 - "Vite Build Tool"
Cohesion: 1.0
Nodes (2): Vite Frontend Build Tool, Vite Logo SVG Icon

### Community 56 - "Tailwind Config"
Cohesion: 1.0
Nodes (0): 

### Community 57 - "Vite Config"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "PostCSS Config"
Cohesion: 1.0
Nodes (0): 

### Community 59 - "App Entry Point"
Cohesion: 1.0
Nodes (0): 

### Community 60 - "Vite Env Types"
Cohesion: 1.0
Nodes (0): 

### Community 61 - "Plan Types"
Cohesion: 1.0
Nodes (0): 

### Community 62 - "Button Component"
Cohesion: 1.0
Nodes (0): 

### Community 63 - "Floating Composer"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Gate Alert Component"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Landing Page"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Backend Init"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Backend Init"
Cohesion: 1.0
Nodes (0): 

### Community 68 - "Backend Init"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Backend Init"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Backend Init"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Backend Init"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "Agent Run Method"
Cohesion: 1.0
Nodes (1): Run the PM agent on raw requirements input.          Args:             raw_input

### Community 73 - "Multi-Turn Messages API"
Cohesion: 1.0
Nodes (1): Multi-turn Messages API call (same path as run(), no disk cache).          Used

### Community 74 - "Jsonschema Dependency"
Cohesion: 1.0
Nodes (1): jsonschema Python Package Dependency

### Community 75 - "Dotenv Dependency"
Cohesion: 1.0
Nodes (1): python-dotenv Python Package Dependency

### Community 76 - "PyPDF Dependency"
Cohesion: 1.0
Nodes (1): pypdf Python Package Dependency

### Community 77 - "Python-Docx Dependency"
Cohesion: 1.0
Nodes (1): python-docx Python Package Dependency

### Community 78 - "Input Schema File"
Cohesion: 1.0
Nodes (1): schemas/input_schema.py Input Schema

### Community 79 - "Eval Script"
Cohesion: 1.0
Nodes (1): scripts/run_eval.py Evaluation Script

### Community 80 - "Project Type E Migration"
Cohesion: 1.0
Nodes (1): Project Type E - Migration

### Community 81 - "Project Type F Automation"
Cohesion: 1.0
Nodes (1): Project Type F - Process Automation

### Community 82 - "P2 E2E Run Logs"
Cohesion: 1.0
Nodes (1): P2 Results E2E HITL Run Logs

### Community 83 - "E2E Log Format"
Cohesion: 1.0
Nodes (1): P2 E2E Scripted Run Log Format

### Community 84 - "P1 Eval Scorecard"
Cohesion: 1.0
Nodes (1): P1 Results Eval Scorecard Directory

### Community 85 - "TC-03 API Gateway"
Cohesion: 1.0
Nodes (1): TC-03 Medium Input API Gateway

## Knowledge Gaps
- **179 isolated node(s):** `Unit tests for Project 2 approval gate rules (no HTTP).`, `Mis-tagged 'Before planning' must not block if WBS is present (v16.2 rubric alig`, `Steps 1–4 merge after refinement — deterministic lock without live LLM.`, `Edge case tests for PM Digital Twin agent. Malformed/empty/boundary inputs shoul`, `Test edge cases and boundary conditions.` (+174 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `App Root`** (2 nodes): `App()`, `App.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Card Curtain Reveal`** (2 nodes): `useCardCurtainRevealContext()`, `card-curtain-reveal.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Studio Shine Border`** (2 nodes): `StudioShineBorder()`, `studio-shine-border.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Plan Sidebar`** (2 nodes): `formatChatWhen()`, `plan-sidebar.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Plan Working Loader`** (2 nodes): `PlanWorkingLoader()`, `plan-working-loader.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Plan Refine Exchange`** (2 nodes): `Bubble()`, `plan-refine-exchange.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Reduced Motion Hook`** (2 nodes): `usePrefersReducedMotion()`, `use-prefers-reduced-motion.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Thread Preview`** (2 nodes): `threadMessagePreview()`, `thread-preview.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `UI Utilities`** (2 nodes): `utils.ts`, `cn()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tech Stack & Langfuse`** (2 nodes): `Technology Stack Table`, `langfuse Python Package Dependency`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TC-02 Customer Dashboard`** (2 nodes): `TC-02 Good Input Customer Dashboard Enhancement`, `PagerDuty Alerting Integration`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Vite Build Tool`** (2 nodes): `Vite Frontend Build Tool`, `Vite Logo SVG Icon`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tailwind Config`** (1 nodes): `tailwind.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Vite Config`** (1 nodes): `vite.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PostCSS Config`** (1 nodes): `postcss.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `App Entry Point`** (1 nodes): `main.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Vite Env Types`** (1 nodes): `vite-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Plan Types`** (1 nodes): `plan.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Button Component`** (1 nodes): `button.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Floating Composer`** (1 nodes): `plan-floating-composer.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Gate Alert Component`** (1 nodes): `gate-alert.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Landing Page`** (1 nodes): `LandingPage.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Agent Run Method`** (1 nodes): `Run the PM agent on raw requirements input.          Args:             raw_input`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Multi-Turn Messages API`** (1 nodes): `Multi-turn Messages API call (same path as run(), no disk cache).          Used`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Jsonschema Dependency`** (1 nodes): `jsonschema Python Package Dependency`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dotenv Dependency`** (1 nodes): `python-dotenv Python Package Dependency`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PyPDF Dependency`** (1 nodes): `pypdf Python Package Dependency`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Python-Docx Dependency`** (1 nodes): `python-docx Python Package Dependency`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Input Schema File`** (1 nodes): `schemas/input_schema.py Input Schema`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Eval Script`** (1 nodes): `scripts/run_eval.py Evaluation Script`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Project Type E Migration`** (1 nodes): `Project Type E - Migration`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Project Type F Automation`** (1 nodes): `Project Type F - Process Automation`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `P2 E2E Run Logs`** (1 nodes): `P2 Results E2E HITL Run Logs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `E2E Log Format`** (1 nodes): `P2 E2E Scripted Run Log Format`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `P1 Eval Scorecard`** (1 nodes): `P1 Results Eval Scorecard Directory`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TC-03 API Gateway`** (1 nodes): `TC-03 Medium Input API Gateway`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SchemaValidator` connect `P2 Test Fixtures & Helpers` to `Business Rules Validator`, `Output Schema & Validation`, `Staffing & Overallocation`, `Gate Evaluation Logic`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `PMAgent` connect `P2 Test Fixtures & Helpers` to `Gate Evaluation Logic`, `PMAgent Core Methods`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `PMReport` connect `Output Schema & Validation` to `Input Schema & Pydantic Models`, `P2 Test Fixtures & Helpers`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `SchemaValidator` (e.g. with `TestHighInputQualityAssumptionCap` and `TestBeforePlanningUrgencyConsistency`) actually correct?**
  _`SchemaValidator` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `PMAgent` (e.g. with `Shared helpers for P2 fixture-based tests.` and `Mock Anthropic client for testing without API calls.`) actually correct?**
  _`PMAgent` has 36 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `AgentRunner` (e.g. with `TestRetry` and `Retry tests for PM Digital Twin agent. Mock API failure scenarios should trigger`) actually correct?**
  _`AgentRunner` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `GateState` (e.g. with `Integration tests: HITL gate-as-warning model + refinement flow.  Design: The ga` and `Gate fires but PM can still refine — feedback is their response to the concerns.`) actually correct?**
  _`GateState` has 23 INFERRED edges - model-reasoned connections that need verification._