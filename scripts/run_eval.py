"""
PM Digital Twin — Master Evaluation Runner
Runs all 5 evaluation dimensions and produces a report.

Usage:
  python scripts/run_eval.py --all
  python scripts/run_eval.py --dimension schema
  python scripts/run_eval.py --tc tc-01-perfect
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.main import PMAgent, MODEL_HAIKU, MODEL_SONNET
from agent.validator import SchemaValidator


# ─────────────────────────────────────────────────────────────
# DIMENSION 1: Schema Validation
# ─────────────────────────────────────────────────────────────
def _run_schema_one(tc: dict, agent: PMAgent, max_retries: int = 3) -> dict:
    """Run schema validation for a single test case with rate-limit retry."""
    print(f"  [Schema] Running {tc['id']}...")
    for attempt in range(max_retries):
        try:
            result = agent.run(tc["input"])
            validator = SchemaValidator()
            validation = validator.validate(result["report"])
            return {
                "test_case": tc["id"],
                "passed": validation["valid"],
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            }
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = 65 * (attempt + 1)
                print(f"    [Rate limit] {tc['id']} — waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            return {
                "test_case": tc["id"],
                "passed": False,
                "errors": [str(e)],
                "warnings": []
            }
    return {
        "test_case": tc["id"],
        "passed": False,
        "errors": ["Rate limit exceeded after all retries"],
        "warnings": []
    }


def run_schema_validation(test_cases: list, agent: PMAgent, workers: int = 5) -> dict:
    """Every output must pass schema validation. Target: 100%."""
    results = [None] * len(test_cases)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_schema_one, tc, agent): i
                   for i, tc in enumerate(test_cases)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    passed = sum(1 for r in results if r["passed"])
    return {
        "dimension": "Schema Validation",
        "target": "100%",
        "result": f"{passed}/{len(results)} ({round(passed/len(results)*100)}%)",
        "passed": passed == len(results),
        "details": results
    }


# ─────────────────────────────────────────────────────────────
# DIMENSION 2: Consistency (Determinism)
# ─────────────────────────────────────────────────────────────
def run_consistency_test(tc_perfect: dict, agent: PMAgent, runs: int = 5) -> dict:
    """Same input should produce consistent output. Target: confidence score variance < 5."""
    print(f"  [Consistency] Running TC-01 {runs} times...")
    scores = []
    types = []
    sdlc_approaches = []
    risk_counts = []

    for i in range(runs):
        try:
            result = agent.run(tc_perfect["input"])
            report = result["report"]
            score = report.get("pm_confidence_score", {}).get("score", 0)
            ptype = report.get("report_metadata", {}).get("project_type", "UNKNOWN")
            sdlc = report.get("report_metadata", {}).get("sdlc_approach", "UNKNOWN")
            risks = len(report.get("risk_register", []))
            scores.append(score)
            types.append(ptype)
            sdlc_approaches.append(sdlc)
            risk_counts.append(risks)
            print(f"    Run {i+1}: score={score}, type={ptype}, sdlc={sdlc}, risks={risks}")
            time.sleep(1)  # Avoid rate limiting
        except Exception as e:
            print(f"    Run {i+1}: ERROR — {e}")

    if not scores:
        return {"dimension": "Consistency", "passed": False, "error": "All runs failed"}

    score_variance = max(scores) - min(scores)
    type_consistent = len(set(types)) == 1
    sdlc_consistent = len(set(sdlc_approaches)) == 1
    risk_variance = max(risk_counts) - min(risk_counts)

    return {
        "dimension": "Consistency",
        "target": "Score variance < 5, type identical across runs, SDLC consistent",
        "result": {
            "score_variance": score_variance,
            "score_range": f"{min(scores)}-{max(scores)}",
            "type_consistent": type_consistent,
            "types_seen": list(set(types)),
            "sdlc_consistent": sdlc_consistent,
            "sdlc_approaches_seen": list(set(sdlc_approaches)),
            "risk_count_variance": risk_variance
        },
        "passed": score_variance < 5 and type_consistent and sdlc_consistent
    }


# ─────────────────────────────────────────────────────────────
# DIMENSION 3: Reasoning Quality Rubric
# ─────────────────────────────────────────────────────────────
def run_rubric_scoring(report: dict) -> dict:
    """
    Score output quality on 5 dimensions (1-5 each).
    Partially automated — flags issues for human review.
    Target: average > 3.5
    """
    scores = {}

    # 3a: Assumption Quality
    assumptions = report.get("assumption_log", [])
    has_pmi = all("pmi_basis" in a and len(a.get("pmi_basis", "")) > 5 for a in assumptions)
    has_consequences = all("consequence" in a and len(a.get("consequence", "")) > 10 for a in assumptions)
    assumption_count = len(assumptions)

    if assumption_count >= 3 and has_pmi and has_consequences:
        scores["assumption_quality"] = 5
    elif assumption_count >= 2 and has_pmi:
        scores["assumption_quality"] = 3
    elif assumption_count >= 1:
        scores["assumption_quality"] = 2
    else:
        scores["assumption_quality"] = 1

    # 3b: Plan Completeness
    phases = report.get("project_plan", {}).get("phases", [])
    total_pct = sum(p.get("percentage_of_total", 0) for p in phases)
    phase_1_ok = any(p.get("phase_number") == 1 and p.get("percentage_of_total", 0) >= 10 for p in phases)
    phase_4_ok = any(p.get("phase_number") == 4 and p.get("percentage_of_total", 0) >= 15 for p in phases)

    if len(phases) == 5 and phase_1_ok and phase_4_ok and 95 <= total_pct <= 105:
        scores["plan_completeness"] = 5
    elif len(phases) == 5 and (phase_1_ok or phase_4_ok):
        scores["plan_completeness"] = 3
    elif len(phases) >= 3:
        scores["plan_completeness"] = 2
    else:
        scores["plan_completeness"] = 1

    # 3c: Risk Realism (automated checks)
    risks = report.get("risk_register", [])
    has_critical = any(r.get("score") == "CRITICAL" for r in risks)
    has_all_fields = all(
        all(f in r for f in ["trigger", "mitigation", "contingency"])
        for r in risks
    )
    categories_used = len(set(r.get("category") for r in risks))

    if len(risks) >= 5 and has_all_fields and categories_used >= 3:
        scores["risk_realism"] = 5
    elif len(risks) >= 3 and has_all_fields:
        scores["risk_realism"] = 3
    elif len(risks) >= 3:
        scores["risk_realism"] = 2
    else:
        scores["risk_realism"] = 1

    # 3d: Staffing Validity
    staffing = report.get("staffing_plan", [])
    no_over_allocation = all(r.get("allocation_percent", 0) <= 80 for r in staffing)
    has_qa = any("qa" in r.get("role", "").lower() or "test" in r.get("role", "").lower() for r in staffing)
    has_pm = any("pm" in r.get("role", "").lower() or "project manager" in r.get("role", "").lower() for r in staffing)

    if no_over_allocation and has_qa and has_pm:
        scores["staffing_validity"] = 5
    elif no_over_allocation and (has_qa or has_pm):
        scores["staffing_validity"] = 3
    elif no_over_allocation:
        scores["staffing_validity"] = 2
    else:
        scores["staffing_validity"] = 1

    # 3e: Internal Consistency (automated)
    # Check if risks reference plan tasks (via risk flags)
    risk_flagged_tasks = [
        t for p in report.get("project_plan", {}).get("phases", [])
        for t in p.get("tasks", [])
        if t.get("risk_flag")
    ]
    has_flagged_tasks = len(risk_flagged_tasks) > 0
    has_open_questions = len(report.get("open_questions", [])) > 0

    if has_flagged_tasks and has_open_questions and len(risks) >= 3:
        scores["internal_consistency"] = 5
    elif has_flagged_tasks or has_open_questions:
        scores["internal_consistency"] = 3
    else:
        scores["internal_consistency"] = 2

    # 3f: SDLC Approach (v1.1.0) - Check if SDLC approach is present
    metadata = report.get("report_metadata", {})
    has_sdlc = "sdlc_approach" in metadata and metadata.get("sdlc_approach") in ["Predictive", "Adaptive", "Hybrid"]
    has_sdlc_rationale = "sdlc_rationale" in metadata and len(metadata.get("sdlc_rationale", "")) > 5
    
    if has_sdlc and has_sdlc_rationale:
        scores["sdlc_approach"] = 5
    elif has_sdlc:
        scores["sdlc_approach"] = 3
    else:
        scores["sdlc_approach"] = 1

    # 3g: Critical Path Calculation (v1.1.0) - Check for critical_path and slack_days
    all_tasks = [t for p in report.get("project_plan", {}).get("phases", []) for t in p.get("tasks", [])]
    tasks_with_critical_path = [t for t in all_tasks if "critical_path" in t]
    tasks_with_slack = [t for t in all_tasks if "slack_days" in t]
    
    has_critical_path_summary = "critical_path_summary" in report.get("project_plan", {})
    
    if all_tasks and len(tasks_with_critical_path) == len(all_tasks) and len(tasks_with_slack) == len(all_tasks) and has_critical_path_summary:
        scores["critical_path"] = 5
    elif all_tasks and (len(tasks_with_critical_path) > 0 or has_critical_path_summary):
        scores["critical_path"] = 3
    else:
        scores["critical_path"] = 1

    # 3h: Assumption Source (v1.1.0) - Check for source field on assumptions
    assumptions = report.get("assumption_log", [])
    assumptions_with_source = [a for a in assumptions if "source" in a]
    
    if assumptions and len(assumptions_with_source) == len(assumptions):
        scores["assumption_source"] = 5
    elif assumptions_with_source:
        scores["assumption_source"] = 3
    else:
        scores["assumption_source"] = 1

    average = round(sum(scores.values()) / len(scores), 2)

    return {
        "dimension": "Reasoning Quality",
        "target": "Average > 3.5/5",
        "scores": scores,
        "average": average,
        "passed": average > 3.5,
        "human_review_needed": [
            "Verify risks are specific to input (not generic)",
            "Verify assumption PMI references are accurate",
            "Verify action items follow from identified risks"
        ]
    }


# ─────────────────────────────────────────────────────────────
# DIMENSION 4: Edge Case Handling
# ─────────────────────────────────────────────────────────────

EDGE_CASE_EXPECTATIONS = {
    "tc-01": {
        "min_confidence": 75,
        "max_assumptions": 3,
        "must_classify": ["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"],
        "must_have_sdlc": True,
        "must_have_critical_path": True
    },
    "tc-04": {
        "max_confidence": 50,
        "min_assumptions": 5,
        "must_flag_risks": True,
        "must_have_nfr_assumptions": True,  # Vague input should trigger NFR assumptions
        # Viability check: No constraints provided, should skip viability check
        "viability_should_be_none": True
    },
    "tc-05": {
        "max_confidence": 40,
        "must_detect_contradiction": True,
        # Viability check: Has budget ($5,000) and deadline (2 weeks)
        # Expected: NOT_VIABLE, BOTH gaps, scoping_options >= 2
        "viability_status": "NOT_VIABLE",
        "viability_gap_type": "BOTH",
        "viability_min_scoping_options": 2
    },
    "tc-09": {
        "must_have_risk_score": ["CRITICAL", "HIGH"],
        "must_flag_timeline": True,
        # Viability check: Has deadline (2 weeks), no budget
        # Expected: NOT_VIABLE (schedule), SCHEDULE gap, scoping_options >= 2
        "viability_status": "NOT_VIABLE",
        "viability_gap_type": "SCHEDULE",
        "viability_min_scoping_options": 2
    },
    "tc-10": {
        # Solo developer on 6-month project - should flag staffing gap
        "must_flag_staffing_gap": True,
        "max_confidence": 50,  # Low confidence due to unrealistic staffing
        # Viability check: Has budget ($100k) and deadline (6 months = 24 weeks)
        # Expected: NOT_VIABLE - agent should recommend additional staff to make this viable,
        # which pushes cost above $100K threshold, so BOTH (budget + schedule)
        "viability_status": "NOT_VIABLE",
        "viability_gap_type": "BOTH",
        "viability_min_scoping_options": 2
    }
}

def _run_edge_case_one(tc: dict, agent: PMAgent, max_retries: int = 3) -> dict:
    """Run edge case checks for a single test case with rate-limit retry."""
    print(f"  [Edge Case] Running {tc['id']}...")
    for attempt in range(max_retries):
        try:
            return _run_edge_case_inner(tc, agent)
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = 65 * (attempt + 1)
                print(f"    [Rate limit] {tc['id']} — waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            return {
                "test_case": tc["id"],
                "overall_passed": False,
                "error": str(e)
            }
    return {
        "test_case": tc["id"],
        "overall_passed": False,
        "error": "Rate limit exceeded after all retries"
    }


def _run_edge_case_inner(tc: dict, agent: PMAgent) -> dict:
    """Core edge case logic (extracted for retry wrapper)."""
    try:
        result = agent.run(tc["input"])
        report = result["report"]
        validator = SchemaValidator()
        validation = validator.validate(report)

        tc_result = {
            "test_case": tc["id"],
            "schema_valid": validation["valid"],
            "confidence_score": report.get("pm_confidence_score", {}).get("score"),
            "assumption_count": len(report.get("assumption_log", [])),
            "risk_count": len(report.get("risk_register", [])),
            "project_type": report.get("report_metadata", {}).get("project_type"),
            "checks": []
        }

        expectations = EDGE_CASE_EXPECTATIONS.get(tc["id"], {})
        passed_checks = []

        if "min_confidence" in expectations:
            score = tc_result["confidence_score"] or 0
            passed = score >= expectations["min_confidence"]
            passed_checks.append(passed)
            tc_result["checks"].append({
                "check": f"Confidence >= {expectations['min_confidence']}",
                "passed": passed, "actual": score
            })

        if "max_confidence" in expectations:
            score = tc_result["confidence_score"] or 100
            passed = score <= expectations["max_confidence"]
            passed_checks.append(passed)
            tc_result["checks"].append({
                "check": f"Confidence <= {expectations['max_confidence']} (low quality input)",
                "passed": passed, "actual": score
            })

        if "min_assumptions" in expectations:
            count = tc_result["assumption_count"]
            passed = count >= expectations["min_assumptions"]
            passed_checks.append(passed)
            tc_result["checks"].append({
                "check": f"Assumptions >= {expectations['min_assumptions']}",
                "passed": passed, "actual": count
            })

        if expectations.get("must_have_sdlc"):
            metadata = report.get("report_metadata", {})
            has_sdlc = "sdlc_approach" in metadata and metadata.get("sdlc_approach") in ["Predictive", "Adaptive", "Hybrid"]
            passed_checks.append(has_sdlc)
            tc_result["checks"].append({
                "check": "SDLC approach present in report_metadata",
                "passed": has_sdlc, "actual": metadata.get("sdlc_approach", "MISSING")
            })

        if expectations.get("must_have_critical_path"):
            all_tasks = [t for p in report.get("project_plan", {}).get("phases", []) for t in p.get("tasks", [])]
            has_critical_path = all("critical_path" in t and "slack_days" in t for t in all_tasks) if all_tasks else False
            has_summary = "critical_path_summary" in report.get("project_plan", {})
            passed = has_critical_path and has_summary
            passed_checks.append(passed)
            tc_result["checks"].append({
                "check": "Critical path and slack_days on all tasks + summary block",
                "passed": passed,
                "actual": f"tasks={len(all_tasks)}, has_cp={has_critical_path}, has_summary={has_summary}"
            })

        if expectations.get("must_have_nfr_assumptions"):
            assumptions = report.get("assumption_log", [])
            nfr_assumptions = [a for a in assumptions if a.get("source") == "nfr"]
            has_nfr = len(nfr_assumptions) > 0
            passed_checks.append(has_nfr)
            tc_result["checks"].append({
                "check": "At least one assumption with source=nfr (Non-Functional Requirement gap)",
                "passed": has_nfr, "actual": f"nfr_assumptions={len(nfr_assumptions)}"
            })

        if expectations.get("must_flag_risks"):
            risks = report.get("risk_register", [])
            has_risks = len(risks) > 0
            passed_checks.append(has_risks)
            tc_result["checks"].append({
                "check": "At least one risk in risk_register",
                "passed": has_risks, "actual": f"risks={len(risks)}"
            })

        if expectations.get("must_detect_contradiction"):
            open_q = report.get("open_questions", [])
            assumptions = report.get("assumption_log", [])
            contradiction_keywords = ["contradict", "inconsistent", "conflict", "mismatch", "unclear"]
            has_contradiction = any(
                any(kw in str(q).lower() for kw in contradiction_keywords) for q in open_q
            ) or any(
                any(kw in str(a.get("assumption", "")).lower() for kw in contradiction_keywords)
                for a in assumptions
            )
            passed_checks.append(has_contradiction)
            tc_result["checks"].append({
                "check": "Detected contradiction in requirements",
                "passed": has_contradiction, "actual": f"has_contradiction={has_contradiction}"
            })

        if expectations.get("must_flag_timeline"):
            risks = report.get("risk_register", [])
            timeline_risks = [r for r in risks if "timeline" in str(r.get("risk", "")).lower() or "deadline" in str(r.get("risk", "")).lower()]
            has_timeline_risk = len(timeline_risks) > 0
            passed_checks.append(has_timeline_risk)
            tc_result["checks"].append({
                "check": "At least one timeline/deadline risk flagged",
                "passed": has_timeline_risk, "actual": f"timeline_risks={len(timeline_risks)}"
            })

        if expectations.get("must_have_risk_score"):
            risks = report.get("risk_register", [])
            required_scores = expectations.get("must_have_risk_score")
            has_required_score = any(r.get("score") in required_scores for r in risks)
            passed_checks.append(has_required_score)
            tc_result["checks"].append({
                "check": f"At least one risk with score in {required_scores}",
                "passed": has_required_score,
                "actual": f"risk_scores={[r.get('score') for r in risks]}"
            })

        if expectations.get("must_flag_staffing_gap"):
            staffing = report.get("staffing_plan", [])
            has_gap_flag = any(r.get("staffing_gap", False) for r in staffing)
            is_solo_overloaded = len(staffing) == 1 and staffing[0].get("allocation_percent", 0) > 80
            has_staffing_risk = any(
                "staff" in r.get("risk", "").lower() or "resource" in r.get("risk", "").lower()
                for r in report.get("risk_register", [])
            )
            flagged = has_gap_flag or is_solo_overloaded or has_staffing_risk
            passed_checks.append(flagged)
            tc_result["checks"].append({
                "check": "Staffing gap flagged for solo developer on 6-month project",
                "passed": flagged,
                "actual": f"gap_flag={has_gap_flag}, solo_overloaded={is_solo_overloaded}, staffing_risk={has_staffing_risk}"
            })

        viability = report.get("project_viability")

        if expectations.get("viability_should_be_none"):
            is_none = viability is None
            passed_checks.append(is_none)
            tc_result["checks"].append({
                "check": "Viability check skipped (no constraints provided)",
                "passed": is_none,
                "actual": f"project_viability={'None' if viability is None else 'present'}"
            })

        if expectations.get("viability_status"):
            expected_status = expectations.get("viability_status")
            actual_status = viability.get("viability_status") if viability else None
            status_match = actual_status == expected_status
            passed_checks.append(status_match)
            tc_result["checks"].append({
                "check": f"Viability status is {expected_status}",
                "passed": status_match, "actual": f"viability_status={actual_status}"
            })

            if expectations.get("viability_gap_type"):
                expected_gap = expectations.get("viability_gap_type")
                actual_gap = viability.get("gap_type") if viability else None
                gap_match = actual_gap == expected_gap
                passed_checks.append(gap_match)
                tc_result["checks"].append({
                    "check": f"Gap type is {expected_gap}",
                    "passed": gap_match, "actual": f"gap_type={actual_gap}"
                })

            if expectations.get("viability_min_scoping_options"):
                min_options = expectations.get("viability_min_scoping_options")
                actual_options = len(viability.get("scoping_options", [])) if viability else 0
                has_options = actual_options >= min_options
                passed_checks.append(has_options)
                tc_result["checks"].append({
                    "check": f"At least {min_options} scoping options when NOT_VIABLE",
                    "passed": has_options, "actual": f"scoping_options={actual_options}"
                })

        tc_result["overall_passed"] = validation["valid"] and all(passed_checks)
        return tc_result

    except Exception as e:
        return {
            "test_case": tc["id"],
            "overall_passed": False,
            "error": str(e)
        }


def run_edge_cases(test_cases: list, agent: PMAgent, workers: int = 5) -> dict:
    """Test edge case handling. Target: > 80% pass rate."""
    results = [None] * len(test_cases)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_edge_case_one, tc, agent): i
                   for i, tc in enumerate(test_cases)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    passed = sum(1 for r in results if r.get("overall_passed"))
    return {
        "dimension": "Edge Case Handling",
        "target": "> 80% pass rate",
        "result": f"{passed}/{len(results)} ({round(passed/len(results)*100) if results else 0}%)",
        "passed": passed / len(results) >= 0.8 if results else False,
        "details": results
    }


# ─────────────────────────────────────────────────────────────
# MAIN EVAL RUNNER
# ─────────────────────────────────────────────────────────────

def load_test_cases(tc_dir: str = "inputs/test-cases") -> list:
    """Load all test case input files."""
    tc_path = Path(tc_dir)
    test_cases = []
    for f in sorted(tc_path.glob("tc-*.txt")):
        test_cases.append({
            "id": f.stem,
            "input": f.read_text(encoding="utf-8").strip()
        })
    return test_cases


def main():
    parser = argparse.ArgumentParser(description="PM Digital Twin Evaluation Suite")
    parser.add_argument("--all", action="store_true", help="Run all dimensions")
    parser.add_argument("--dimension", choices=["schema", "consistency", "rubric", "edge"], help="Run one dimension")
    parser.add_argument("--tc", help="Run specific test case only (e.g. tc-01-perfect)")
    parser.add_argument("--prompt-version", default="v1.4")
    parser.add_argument("--model", default=MODEL_HAIKU,
                        help=f"Model to use. haiku={MODEL_HAIKU}, sonnet={MODEL_SONNET}")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers for schema/edge-case dimensions (default 1). "
                             "Haiku free tier: 10k output tokens/min — 1 worker avoids rate limits.")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"PM DIGITAL TWIN — EVALUATION SUITE")
    print(f"Prompt Version : {args.prompt_version}")
    print(f"Model          : {args.model}")
    print(f"Parallel workers: {args.workers}")
    print(f"Timestamp      : {datetime.utcnow().isoformat()}Z")
    print(f"{'='*60}\n")

    agent = PMAgent(prompt_version=args.prompt_version, model=args.model)
    
    # Warmup skipped — consumes output token budget on rate-limited tiers.
    # Cache still gets primed on first real TC call.
    
    test_cases = load_test_cases()

    if not test_cases:
        print("ERROR: No test cases found in inputs/test-cases/")
        return

    if args.tc:
        test_cases = [tc for tc in test_cases if tc["id"] == args.tc]
        if not test_cases:
            print(f"ERROR: Test case '{args.tc}' not found.")
            return

    print(f"Loaded {len(test_cases)} test cases: {[tc['id'] for tc in test_cases]}\n")

    all_results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prompt_version": args.prompt_version,
        "dimensions": {}
    }

    run_all = args.all or args.dimension is None

    # Dimension 1: Schema
    if run_all or args.dimension == "schema":
        print("[DIMENSION 1] Schema Validation")
        result = run_schema_validation(test_cases, agent, workers=args.workers)
        all_results["dimensions"]["schema_validation"] = result
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  Result: {result['result']} {status}\n")

    # Dimension 2: Consistency
    if run_all or args.dimension == "consistency":
        print("[DIMENSION 2] Consistency Test")
        perfect_tc = next((tc for tc in test_cases if tc["id"] == "tc-01"), test_cases[0])
        result = run_consistency_test(perfect_tc, agent, runs=3)
        all_results["dimensions"]["consistency"] = result
        status = "✅ PASS" if result.get("passed") else "❌ FAIL"
        if "result" in result:
            print(f"  Score Variance: {result['result'].get('score_variance', 'N/A')} {status}\n")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')} {status}\n")

    # Dimension 3: Rubric
    if run_all or args.dimension == "rubric":
        print("[DIMENSION 3] Reasoning Quality Rubric")
        perfect_tc = next((tc for tc in test_cases if tc["id"] == "tc-01"), test_cases[0])
        run_result = agent.run(perfect_tc["input"])
        report = run_result["report"]
        result = run_rubric_scoring(report)
        all_results["dimensions"]["reasoning_quality"] = result
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  Average Score: {result['average']}/5 {status}")
        for dim, score in result["scores"].items():
            print(f"    {dim}: {score}/5")

        # Confidence score sanity check
        assumption_count = len(report.get("assumption_log", []))
        cs = report.get("pm_confidence_score", {})
        cs_score = cs.get("score", "N/A") if isinstance(cs, dict) else cs
        deductions = cs.get("deductions", []) if isinstance(cs, dict) else []
        interpretation = cs.get("interpretation", "MISSING") if isinstance(cs, dict) else "MISSING"
        cap_note = " ← cap ≥5 assumptions applies (≤60)" if assumption_count >= 5 else ""
        print(f"\n  Confidence Score Sanity Check:")
        print(f"    Score          : {cs_score}{cap_note}")
        print(f"    Assumptions    : {assumption_count}")
        print(f"    Deductions     : {len(deductions)}")
        for d in deductions:
            print(f"      -{d.get('amount', '?')}  {d.get('reason', '?')}")
        print(f"    Interpretation : {interpretation}")
        print()

    # Dimension 4: Edge Cases
    if run_all or args.dimension == "edge":
        print("[DIMENSION 4] Edge Case Handling")
        result = run_edge_cases(test_cases, agent, workers=args.workers)
        all_results["dimensions"]["edge_cases"] = result
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  Result: {result['result']} {status}\n")

    # Summary
    print(f"{'='*60}")
    print("EVALUATION SUMMARY")
    print(f"{'='*60}")
    total_dimensions = len(all_results["dimensions"])
    passed_dimensions = sum(1 for d in all_results["dimensions"].values() if d.get("passed"))
    print(f"Dimensions Passed: {passed_dimensions}/{total_dimensions}")

    for dim_name, dim_result in all_results["dimensions"].items():
        status = "✅" if dim_result.get("passed") else "❌"
        print(f"  {status} {dim_result.get('dimension', dim_name)}")

    # Save results
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"eval_{args.prompt_version}_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nFull results saved to: {results_file}")


if __name__ == "__main__":
    main()
