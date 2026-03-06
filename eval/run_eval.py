"""
PM Digital Twin — Master Evaluation Runner
Runs all 5 evaluation dimensions and produces a report.

Usage:
  python eval/run_eval.py --all
  python eval/run_eval.py --dimension schema
  python eval/run_eval.py --tc tc-01
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent import PMAgent
from validator import SchemaValidator


# ─────────────────────────────────────────────────────────────
# DIMENSION 1: Schema Validation
# ─────────────────────────────────────────────────────────────
def run_schema_validation(test_cases: list, agent: PMAgent) -> dict:
    """Every output must pass schema validation. Target: 100%."""
    results = []
    for tc in test_cases:
        print(f"  [Schema] Running {tc['id']}...")
        try:
            result = agent.run(tc["input"])
            validator = SchemaValidator()
            validation = validator.validate(result["report"])
            results.append({
                "test_case": tc["id"],
                "passed": validation["valid"],
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            })
        except Exception as e:
            results.append({
                "test_case": tc["id"],
                "passed": False,
                "errors": [str(e)],
                "warnings": []
            })

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
        "must_have_nfr_assumptions": True  # Vague input should trigger NFR assumptions
    },
    "tc-05": {
        "max_confidence": 40,
        "must_detect_contradiction": True
    },
    "tc-09": {
        "must_have_risk_score": ["CRITICAL", "HIGH"],
        "must_flag_timeline": True
    }
}

def run_edge_cases(test_cases: list, agent: PMAgent) -> dict:
    """Test edge case handling. Target: > 80% pass rate."""
    results = []

    for tc in test_cases:
        print(f"  [Edge Case] Running {tc['id']}...")
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

            # Run expectations if defined
            expectations = EDGE_CASE_EXPECTATIONS.get(tc["id"], {})
            passed_checks = []

            if "min_confidence" in expectations:
                score = tc_result["confidence_score"] or 0
                passed = score >= expectations["min_confidence"]
                passed_checks.append(passed)
                tc_result["checks"].append({
                    "check": f"Confidence >= {expectations['min_confidence']}",
                    "passed": passed,
                    "actual": score
                })

            if "max_confidence" in expectations:
                score = tc_result["confidence_score"] or 100
                passed = score <= expectations["max_confidence"]
                passed_checks.append(passed)
                tc_result["checks"].append({
                    "check": f"Confidence <= {expectations['max_confidence']} (low quality input)",
                    "passed": passed,
                    "actual": score
                })

            if "min_assumptions" in expectations:
                count = tc_result["assumption_count"]
                passed = count >= expectations["min_assumptions"]
                passed_checks.append(passed)
                tc_result["checks"].append({
                    "check": f"Assumptions >= {expectations['min_assumptions']}",
                    "passed": passed,
                    "actual": count
                })

            # v1.1.0: Check for SDLC approach
            if expectations.get("must_have_sdlc"):
                metadata = report.get("report_metadata", {})
                has_sdlc = "sdlc_approach" in metadata and metadata.get("sdlc_approach") in ["Predictive", "Adaptive", "Hybrid"]
                passed_checks.append(has_sdlc)
                tc_result["checks"].append({
                    "check": "SDLC approach present in report_metadata",
                    "passed": has_sdlc,
                    "actual": metadata.get("sdlc_approach", "MISSING")
                })

            # v1.1.0: Check for critical path fields
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

            # v1.1.0: Check for NFR assumptions (vague input should generate NFR gaps)
            if expectations.get("must_have_nfr_assumptions"):
                assumptions = report.get("assumption_log", [])
                nfr_assumptions = [a for a in assumptions if a.get("source") == "nfr"]
                has_nfr = len(nfr_assumptions) > 0
                passed_checks.append(has_nfr)
                tc_result["checks"].append({
                    "check": "At least one assumption with source=nfr (Non-Functional Requirement gap)",
                    "passed": has_nfr,
                    "actual": f"nfr_assumptions={len(nfr_assumptions)}"
                })

            tc_result["overall_passed"] = validation["valid"] and all(passed_checks)
            results.append(tc_result)

        except Exception as e:
            results.append({
                "test_case": tc["id"],
                "overall_passed": False,
                "error": str(e)
            })

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
    parser.add_argument("--tc", help="Run specific test case only")
    parser.add_argument("--prompt-version", default="v1")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"PM DIGITAL TWIN — EVALUATION SUITE")
    print(f"Prompt Version: {args.prompt_version}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print(f"{'='*60}\n")

    agent = PMAgent(prompt_version=args.prompt_version)
    test_cases = load_test_cases()

    if not test_cases:
        print("ERROR: No test cases found in inputs/test-cases/")
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
        result = run_schema_validation(test_cases, agent)
        all_results["dimensions"]["schema_validation"] = result
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  Result: {result['result']} {status}\n")

    # Dimension 2: Consistency
    if run_all or args.dimension == "consistency":
        print("[DIMENSION 2] Consistency Test")
        perfect_tc = next((tc for tc in test_cases if tc["id"] == "tc-01"), test_cases[0])
        result = run_consistency_test(perfect_tc, agent, runs=3)
        all_results["dimensions"]["consistency"] = result
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  Score Variance: {result['result'].get('score_variance', 'N/A')} {status}\n")

    # Dimension 3: Rubric
    if run_all or args.dimension == "rubric":
        print("[DIMENSION 3] Reasoning Quality Rubric")
        perfect_tc = next((tc for tc in test_cases if tc["id"] == "tc-01"), test_cases[0])
        run_result = agent.run(perfect_tc["input"])
        result = run_rubric_scoring(run_result["report"])
        all_results["dimensions"]["reasoning_quality"] = result
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  Average Score: {result['average']}/5 {status}")
        for dim, score in result["scores"].items():
            print(f"    {dim}: {score}/5")
        print()

    # Dimension 4: Edge Cases
    if run_all or args.dimension == "edge":
        print("[DIMENSION 4] Edge Case Handling")
        result = run_edge_cases(test_cases, agent)
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
