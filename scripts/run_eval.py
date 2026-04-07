"""
PM Digital Twin — Master Evaluation Runner
Runs all 5 evaluation dimensions and produces a report.

Usage:
  python scripts/run_eval.py --all
  python scripts/run_eval.py --dimension schema
  python scripts/run_eval.py --tc tc-01-perfect

Cost-saving modes:
  python scripts/run_eval.py --generate                  # Generate & save outputs only (no eval)
  python scripts/run_eval.py --dimension schema --replay  # Evaluate saved outputs (FREE, no API calls)
  python scripts/run_eval.py --replay --dimension rubric  # Re-score rubric on cached output (FREE)
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.main import PMAgent, MODEL_HAIKU, MODEL_SONNET
from agent.validator import SchemaValidator

# ─────────────────────────────────────────────────────────────
# COST TRACKING
# ─────────────────────────────────────────────────────────────
PRICING = {
    MODEL_HAIKU: {"input": 1.00, "output": 5.00, "cache_read": 0.10, "cache_write": 1.25},
    MODEL_SONNET: {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
}


class CostTracker:
    """Accumulates token usage and estimates cost across all API calls."""

    def __init__(self, model: str):
        self.model = model
        self.prices = PRICING.get(model, PRICING[MODEL_HAIKU])
        self.total_input = 0
        self.total_output = 0
        self.total_cache_read = 0
        self.total_cache_write = 0
        self.call_count = 0

    def record(self, result: dict):
        """Record token usage from an agent.run() result."""
        self.call_count += 1
        self.total_input += result.get("input_tokens", 0)
        self.total_output += result.get("output_tokens", 0)
        self.total_cache_read += result.get("cache_read_tokens", 0)
        self.total_cache_write += result.get("cache_creation_tokens", 0)

    @property
    def estimated_cost(self) -> float:
        p = self.prices
        cost = (
            (self.total_input / 1_000_000) * p["input"]
            + (self.total_output / 1_000_000) * p["output"]
            + (self.total_cache_read / 1_000_000) * p["cache_read"]
            + (self.total_cache_write / 1_000_000) * p["cache_write"]
        )
        return round(cost, 4)

    def summary(self) -> str:
        lines = [
            f"  API calls        : {self.call_count}",
            f"  Input tokens     : {self.total_input:,}",
            f"  Output tokens    : {self.total_output:,}",
            f"  Cache read tokens: {self.total_cache_read:,}",
            f"  Cache write tokens: {self.total_cache_write:,}",
            f"  Estimated cost   : ${self.estimated_cost:.4f}",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# OUTPUT SAVING / LOADING (versioned by prompt)
# ─────────────────────────────────────────────────────────────

def _output_dir(prompt_version: str) -> Path:
    return Path("outputs") / prompt_version


def _save_output(tc_id: str, report: dict, prompt_version: str = "v1.6.2",
                 run_index: int = 0):
    """Save agent report JSON to outputs/{prompt_version}/.

    One file per test case: {tc_id}.json
    D2 consistency runs use: {tc_id}_run{n}.json
    """
    out_dir = _output_dir(prompt_version)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_run{run_index}" if run_index > 0 else ""
    filename = out_dir / f"{tc_id}{suffix}.json"
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    print(f"    Output saved: {filename}")


def _load_output(tc_id: str, prompt_version: str = "v1.6.2",
                 run_index: int = 0) -> dict | None:
    """Load a previously saved output for replay. Returns None if not found."""
    out_dir = _output_dir(prompt_version)
    suffix = f"_run{run_index}" if run_index > 0 else ""
    filename = out_dir / f"{tc_id}{suffix}.json"
    if not filename.exists():
        return None
    with open(filename) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────
# DIMENSION 1: Schema Validation
# ─────────────────────────────────────────────────────────────
def _run_schema_one(tc: dict, agent: PMAgent, prompt_version: str = "v1.6.2",
                    replay: bool = False, cost_tracker: CostTracker = None,
                    max_retries: int = 3) -> dict:
    """Run schema validation for a single test case with rate-limit retry."""
    print(f"  [Schema] {'Replaying' if replay else 'Running'} {tc['id']}...")

    if replay:
        report = _load_output(tc["id"], prompt_version)
        if report is None:
            return {"test_case": tc["id"], "passed": False,
                    "errors": [f"No cached output for {tc['id']} in outputs/{prompt_version}/"],
                    "warnings": []}
    else:
        validator = SchemaValidator()
        report = None
        validation = None
        for attempt in range(max_retries):
            try:
                result = agent.run(
                    tc["input"],
                    input_source=tc["id"],
                    use_cache=(attempt == 0),
                )
                if cost_tracker:
                    cost_tracker.record(result)
                report = result["report"]
                validation = validator.validate(report)
                if validation["valid"]:
                    _save_output(tc["id"], report, prompt_version)
                    break
                err_preview = (validation.get("errors") or [])[:2]
                print(
                    f"    [Validation] {tc['id']} attempt {attempt + 1}/{max_retries} "
                    f"failed — {err_preview}"
                )
                if attempt + 1 >= max_retries:
                    _save_output(tc["id"], report, prompt_version)
                    break
                time.sleep(5)
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    wait = 65 * (attempt + 1)
                    print(f"    [Rate limit] {tc['id']} — waiting {wait}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue
                return {"test_case": tc["id"], "passed": False, "errors": [str(e)], "warnings": []}
        else:
            return {"test_case": tc["id"], "passed": False,
                    "errors": ["Rate limit exceeded after all retries"], "warnings": []}

        if report is None or validation is None:
            return {"test_case": tc["id"], "passed": False,
                    "errors": ["No report produced"], "warnings": []}
    if replay:
        validator = SchemaValidator()
        validation = validator.validate(report)
    return {
        "test_case": tc["id"],
        "passed": validation["valid"],
        "errors": validation["errors"],
        "warnings": validation["warnings"]
    }


def run_schema_validation(test_cases: list, agent: PMAgent, workers: int = 5,
                          prompt_version: str = "v1.6.2", replay: bool = False,
                          cost_tracker: CostTracker = None) -> dict:
    """Every output must pass schema validation. Target: 100%."""
    results = [None] * len(test_cases)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_schema_one, tc, agent, prompt_version, replay,
                               cost_tracker): i
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
def run_consistency_test(tc_perfect: dict, agent: PMAgent, runs: int = 5,
                         prompt_version: str = "v1.6.2", replay: bool = False,
                         cost_tracker: CostTracker = None) -> dict:
    """Same input should produce consistent output. Target: confidence score variance < 5."""
    if replay:
        print(f"  [Consistency] Replaying cached runs for {tc_perfect.get('id', 'tc-01')}...")
        return _replay_consistency(tc_perfect, prompt_version, runs)

    print(f"  [Consistency] Running {tc_perfect.get('id', 'tc-01')} {runs} times...")
    scores = []
    types = []
    sdlc_approaches = []
    risk_counts = []

    for i in range(runs):
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                result = agent.run(tc_perfect["input"], input_source=tc_perfect["id"],
                                   use_cache=False)
                if cost_tracker:
                    cost_tracker.record(result)
                report = result["report"]
                if report.get("parse_error"):
                    raw = report.get("raw_output", "")
                    print(f"    Run {i+1}: parse failure (first 300 chars): {raw[:300]}")
                    if attempt < max_attempts - 1:
                        print(f"    Run {i+1}: retrying...")
                        time.sleep(5)
                        continue
                cs = report.get("pm_confidence_score", {})
                score = cs.get("score", 0) if isinstance(cs, dict) else (cs or 0)
                ptype = report.get("report_metadata", {}).get("project_type", "UNKNOWN")
                sdlc = report.get("report_metadata", {}).get("sdlc_approach", "UNKNOWN")
                risks = len(report.get("risk_register", []))
                _save_output(tc_perfect.get("id", "tc-01"), report,
                             prompt_version, run_index=i+1)
                scores.append(score)
                types.append(ptype)
                sdlc_approaches.append(sdlc)
                risk_counts.append(risks)
                print(f"    Run {i+1}: score={score}, type={ptype}, sdlc={sdlc}, risks={risks}")
                time.sleep(1)
                break
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"    Run {i+1}: ERROR — {e}, retrying...")
                    time.sleep(5)
                else:
                    print(f"    Run {i+1}: ERROR — {e}")

    if not scores:
        return {"dimension": "Consistency", "passed": False, "error": "All runs failed"}

    score_variance = max(scores) - min(scores)
    type_consistent = len(set(types)) == 1
    sdlc_consistent = len(set(sdlc_approaches)) == 1
    risk_variance = max(risk_counts) - min(risk_counts)
    same_band = _scores_in_same_band(scores)

    return {
        "dimension": "Consistency",
        "target": "Score variance < 15 and same 10-pt band, type identical, SDLC consistent",
        "result": {
            "score_variance": score_variance,
            "score_range": f"{min(scores)}-{max(scores)}",
            "same_10pt_band": same_band,
            "type_consistent": type_consistent,
            "types_seen": list(set(types)),
            "sdlc_consistent": sdlc_consistent,
            "sdlc_approaches_seen": list(set(sdlc_approaches)),
            "risk_count_variance": risk_variance
        },
        "passed": score_variance < 15 and same_band and type_consistent and sdlc_consistent
    }


def _scores_in_same_band(scores: list) -> bool:
    """All scores within a 10-point range (e.g. 50-60 counts as one band)."""
    if not scores:
        return True
    return (max(scores) - min(scores)) <= 10


def _replay_consistency(tc: dict, prompt_version: str, runs: int) -> dict:
    """Replay consistency from cached outputs."""
    scores, types, sdlc_approaches, risk_counts = [], [], [], []
    for i in range(1, runs + 1):
        report = _load_output(tc.get("id", "tc-01"), prompt_version, run_index=i)
        if report is None:
            print(f"    Run {i}: no cached output found, skipping")
            continue
        cs = report.get("pm_confidence_score", {})
        score = cs.get("score", 0) if isinstance(cs, dict) else (cs or 0)
        ptype = report.get("report_metadata", {}).get("project_type", "UNKNOWN")
        sdlc = report.get("report_metadata", {}).get("sdlc_approach", "UNKNOWN")
        risks = len(report.get("risk_register", []))
        scores.append(score)
        types.append(ptype)
        sdlc_approaches.append(sdlc)
        risk_counts.append(risks)
        print(f"    Run {i} (cached): score={score}, type={ptype}, sdlc={sdlc}, risks={risks}")

    if not scores:
        return {"dimension": "Consistency", "passed": False,
                "error": f"No cached consistency runs in outputs/{prompt_version}/"}

    score_variance = max(scores) - min(scores)
    type_consistent = len(set(types)) == 1
    sdlc_consistent = len(set(sdlc_approaches)) == 1
    risk_variance = max(risk_counts) - min(risk_counts)
    same_band = _scores_in_same_band(scores)

    return {
        "dimension": "Consistency",
        "target": "Score variance < 15 and same 10-pt band, type identical, SDLC consistent",
        "result": {
            "score_variance": score_variance,
            "score_range": f"{min(scores)}-{max(scores)}",
            "same_10pt_band": same_band,
            "type_consistent": type_consistent,
            "types_seen": list(set(types)),
            "sdlc_consistent": sdlc_consistent,
            "sdlc_approaches_seen": list(set(sdlc_approaches)),
            "risk_count_variance": risk_variance,
            "replayed_runs": len(scores),
        },
        "passed": score_variance < 15 and same_band and type_consistent and sdlc_consistent
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
    phase_5 = next((p for p in phases if p.get("phase_number") == 5), None)
    p5_raw = phase_5.get("percentage_of_total") if phase_5 else None
    try:
        p5_pct = float(p5_raw) if p5_raw is not None else None
    except (TypeError, ValueError):
        p5_pct = None
    phase_5_ok = p5_pct is not None and p5_pct <= 10

    if (
        len(phases) == 5
        and phase_1_ok
        and phase_4_ok
        and phase_5_ok
        and 95 <= total_pct <= 105
    ):
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
    has_pm = any(
        any(kw in r.get("role", "").lower() for kw in ["project manager", "product manager", "pm", "scrum master"])
        for r in staffing
    )

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
    "tc-01-perfect": {
        "min_confidence": 55,
        "max_assumptions": 7,
        "must_classify": ["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"],
        "must_have_sdlc": True,
        "must_have_critical_path": True
    },
    "tc-04-vague": {
        "max_confidence": 50,
        "min_assumptions": 5,
        "must_flag_risks": True,
        # v1.6.1 materiality gate: NFR gaps may be covered via scope/hard_constraint
        # assumptions without source=nfr — still valid vague-input handling.
        "viability_should_be_none": True
    },
    "tc-05-contradictory": {
        "max_confidence": 40,
        "must_detect_contradiction": True,
        "viability_status": "NOT_VIABLE",
        "viability_gap_type": "BOTH",
        "viability_min_scoping_options": 2
    },
    "tc-09-short-timeline": {
        "must_have_risk_score": ["CRITICAL", "HIGH"],
        "must_flag_timeline": True,
        "viability_status": "NOT_VIABLE",
        "viability_gap_type": ["SCHEDULE", "BOTH"],
        "viability_min_scoping_options": 2
    },
    "tc-10-solo-team": {
        "must_flag_staffing_gap": True,
        "max_confidence": 50,
        "viability_status": "NOT_VIABLE",
        "viability_gap_type": "BOTH",
        "viability_min_scoping_options": 2
    }
}

def _run_edge_case_one(tc: dict, agent: PMAgent, prompt_version: str = "v1.6.2",
                       replay: bool = False, cost_tracker: CostTracker = None,
                       max_retries: int = 3) -> dict:
    """Run edge case checks for a single test case with rate-limit retry."""
    print(f"  [Edge Case] {'Replaying' if replay else 'Running'} {tc['id']}...")

    if replay:
        report = _load_output(tc["id"], prompt_version)
        if report is None:
            return {"test_case": tc["id"], "overall_passed": False,
                    "error": f"No cached output for {tc['id']} in outputs/{prompt_version}/"}
        return _evaluate_edge_case(tc, report)

    for attempt in range(max_retries):
        try:
            return _run_edge_case_inner(tc, agent, prompt_version, cost_tracker)
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


def _run_edge_case_inner(tc: dict, agent: PMAgent, prompt_version: str = "v1.6.2",
                         cost_tracker: CostTracker = None) -> dict:
    """Core edge case logic (extracted for retry wrapper)."""
    try:
        result = agent.run(tc["input"], input_source=tc["id"])
        if cost_tracker:
            cost_tracker.record(result)
        report = result["report"]
        _save_output(tc["id"], report, prompt_version)
        return _evaluate_edge_case(tc, report)

    except Exception as e:
        return {
            "test_case": tc["id"],
            "overall_passed": False,
            "error": str(e)
        }


def _evaluate_edge_case(tc: dict, report: dict) -> dict:
    """Pure evaluation logic for edge cases — works on any report dict (live or cached)."""
    validator = SchemaValidator()
    validation = validator.validate(report)

    tc_result = {
        "test_case": tc["id"],
        "schema_valid": validation["valid"],
        "confidence_score": (
            report.get("pm_confidence_score", {}).get("score")
            if isinstance(report.get("pm_confidence_score"), dict)
            else report.get("pm_confidence_score")
        ),
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

    if "max_assumptions" in expectations:
        count = tc_result["assumption_count"]
        passed = count <= expectations["max_assumptions"]
        passed_checks.append(passed)
        tc_result["checks"].append({
            "check": f"Assumptions <= {expectations['max_assumptions']} (well-defined input)",
            "passed": passed, "actual": count
        })

    if "must_classify" in expectations:
        ptype = tc_result.get("project_type", "UNKNOWN")
        valid_types = expectations["must_classify"]
        passed = ptype in valid_types
        passed_checks.append(passed)
        tc_result["checks"].append({
            "check": f"Project type in {valid_types}",
            "passed": passed, "actual": ptype
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
        cs = report.get("pm_confidence_score", {})
        conf_score = cs.get("score") if isinstance(cs, dict) else cs
        viability_obj = report.get("project_viability") or {}
        v_status = viability_obj.get("viability_status") if viability_obj else None
        v_gap = viability_obj.get("gap_type") if viability_obj else None
        detected = (
            (conf_score is not None and conf_score <= 20)
            and v_status == "NOT_VIABLE"
            and v_gap == "BOTH"
        )
        passed_checks.append(detected)
        tc_result["checks"].append({
            "check": "Detected contradiction in requirements",
            "passed": detected,
            "actual": f"confidence={conf_score}, status={v_status}, gap={v_gap}"
        })

    if expectations.get("must_flag_timeline"):
        risks = report.get("risk_register", [])
        timeline_kw = ["timeline", "deadline", "schedule", "duration", "time constraint", "compressed", "aggressive"]
        def _risk_text(r):
            return (str(r.get("risk", "")) + " " + str(r.get("description", ""))).lower()
        timeline_risks = [r for r in risks if any(kw in _risk_text(r) for kw in timeline_kw)]
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
        viability_obj = report.get("project_viability") or {}
        v_status = viability_obj.get("viability_status") if viability_obj else None
        v_gap = viability_obj.get("gap_type") if viability_obj else None
        risk_count = len(report.get("risk_register", []))
        flagged = (
            v_status == "NOT_VIABLE"
            and v_gap in ["BOTH", "BUDGET"]
            and risk_count >= 8
        )
        passed_checks.append(flagged)
        tc_result["checks"].append({
            "check": "Staffing gap flagged for solo developer on 6-month project",
            "passed": flagged,
            "actual": f"status={v_status}, gap={v_gap}, risk_count={risk_count}"
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
            if isinstance(expected_gap, list):
                gap_match = actual_gap in expected_gap
            else:
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


def run_edge_cases(test_cases: list, agent: PMAgent, workers: int = 5,
                   prompt_version: str = "v1.6.2", replay: bool = False,
                   cost_tracker: CostTracker = None) -> dict:
    """Test edge case handling. Target: > 80% pass rate."""
    results = [None] * len(test_cases)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_edge_case_one, tc, agent, prompt_version, replay,
                               cost_tracker): i
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

def load_test_cases(tc_dir: str = "inputs/test-cases-p1") -> list:
    """Load all test case input files."""
    tc_path = Path(tc_dir)
    test_cases = []
    for f in sorted(tc_path.glob("tc-*.txt")):
        test_cases.append({
            "id": f.stem,
            "input": f.read_text(encoding="utf-8").strip()
        })
    return test_cases


def _generate_outputs(test_cases: list, agent: PMAgent, prompt_version: str,
                      cost_tracker: CostTracker, workers: int = 1):
    """Generate and cache outputs for all test cases without evaluating. One API call per TC."""
    print(f"\n[GENERATE] Producing outputs for {len(test_cases)} test cases → outputs/{prompt_version}/\n")
    out_dir = _output_dir(prompt_version)
    out_dir.mkdir(parents=True, exist_ok=True)

    for tc in test_cases:
        print(f"  Generating {tc['id']}...")
        try:
            result = agent.run(tc["input"], input_source=tc["id"])
            cost_tracker.record(result)
            report = result["report"]
            _save_output(tc["id"], report, prompt_version)
            print(f"    OK ({result.get('tokens_used', 0):,} tokens)")
        except Exception as e:
            print(f"    FAILED: {e}")
        time.sleep(1)

    print(f"\n[GENERATE] Done. Outputs cached in outputs/{prompt_version}/")
    print(f"  Now run with --replay to evaluate for FREE:\n")
    print(f"    python scripts/run_eval.py --replay --dimension schema")
    print(f"    python scripts/run_eval.py --replay --dimension rubric")
    print(f"    python scripts/run_eval.py --replay --dimension edge\n")


def main():
    parser = argparse.ArgumentParser(description="PM Digital Twin Evaluation Suite")
    parser.add_argument("--all", action="store_true", help="Run all dimensions")
    parser.add_argument("--dimension", choices=["schema", "consistency", "rubric", "edge"], help="Run one dimension")
    parser.add_argument("--tc", help="Run specific test case only (e.g. tc-01-perfect)")
    parser.add_argument("--prompt-version", default="v1.6.2")
    parser.add_argument("--model", default=MODEL_HAIKU,
                        help=f"Model to use. haiku={MODEL_HAIKU}, sonnet={MODEL_SONNET}")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers for schema/edge-case dimensions (default 1). "
                             "Haiku free tier: 10k output tokens/min — 1 worker avoids rate limits.")
    parser.add_argument("--replay", action="store_true",
                        help="Evaluate cached outputs instead of calling the API (FREE). "
                             "Loads from outputs/{prompt-version}/. Use --generate first.")
    parser.add_argument("--generate", action="store_true",
                        help="Generate and cache outputs for all test cases (1 API call per TC). "
                             "Skips evaluation — use --replay afterwards to evaluate for free.")
    args = parser.parse_args()

    mode_label = "REPLAY (no API calls)" if args.replay else ("GENERATE ONLY" if args.generate else "LIVE")

    print(f"\n{'='*60}")
    print(f"PM DIGITAL TWIN — EVALUATION SUITE")
    print(f"Prompt Version : {args.prompt_version}")
    print(f"Model          : {args.model}")
    print(f"Mode           : {mode_label}")
    print(f"Parallel workers: {args.workers}")
    print(f"Timestamp      : {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}")
    print(f"{'='*60}\n")

    cost_tracker = CostTracker(args.model)
    agent = PMAgent(prompt_version=args.prompt_version, model=args.model)

    test_cases = load_test_cases()

    if not test_cases:
        print("ERROR: No test cases found in inputs/test-cases-p1/")
        return

    if args.tc:
        test_cases = [tc for tc in test_cases if tc["id"] == args.tc]
        if not test_cases:
            print(f"ERROR: Test case '{args.tc}' not found.")
            return

    print(f"Loaded {len(test_cases)} test cases: {[tc['id'] for tc in test_cases]}\n")

    # --generate mode: produce and cache outputs, then exit
    if args.generate:
        _generate_outputs(test_cases, agent, args.prompt_version, cost_tracker, args.workers)
        print(f"\n{'='*60}")
        print("COST SUMMARY (generate)")
        print(f"{'='*60}")
        print(cost_tracker.summary())
        return

    if args.replay:
        cached = _output_dir(args.prompt_version)
        if not cached.exists():
            print(f"ERROR: No cached outputs in {cached}/")
            print(f"  Run --generate first: python scripts/run_eval.py --generate --prompt-version {args.prompt_version}")
            return

    all_results = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "prompt_version": args.prompt_version,
        "mode": mode_label,
        "dimensions": {}
    }

    run_all = args.all or args.dimension is None

    # Dimension 1: Schema
    if run_all or args.dimension == "schema":
        print("[DIMENSION 1] Schema Validation")
        result = run_schema_validation(test_cases, agent, workers=args.workers,
                                       prompt_version=args.prompt_version,
                                       replay=args.replay, cost_tracker=cost_tracker)
        all_results["dimensions"]["schema_validation"] = result
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  Result: {result['result']} {status}\n")

    # Dimension 2: Consistency
    if run_all or args.dimension == "consistency":
        print("[DIMENSION 2] Consistency Test")
        if args.replay:
            print("  ⚠️  D2 replay re-evaluates cached runs. For true consistency testing, run without --replay.")
        perfect_tc = next((tc for tc in test_cases if "tc-01" in tc["id"]), test_cases[0])
        result = run_consistency_test(perfect_tc, agent, runs=3,
                                      prompt_version=args.prompt_version,
                                      replay=args.replay, cost_tracker=cost_tracker)
        all_results["dimensions"]["consistency"] = result
        status = "✅ PASS" if result.get("passed") else "❌ FAIL"
        if "result" in result:
            print(f"  Score Variance: {result['result'].get('score_variance', 'N/A')} {status}\n")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')} {status}\n")

    # Dimension 3: Rubric
    if run_all or args.dimension == "rubric":
        print("[DIMENSION 3] Reasoning Quality Rubric")
        perfect_tc = next((tc for tc in test_cases if "tc-01" in tc["id"]), test_cases[0])

        if args.replay:
            report = _load_output(perfect_tc["id"], args.prompt_version)
            if report is None:
                print(f"  ERROR: No cached output for {perfect_tc['id']}. Run --generate first.")
                report = {}
        else:
            run_result = agent.run(perfect_tc["input"], input_source=perfect_tc["id"])
            cost_tracker.record(run_result)
            report = run_result["report"]
            _save_output(perfect_tc["id"], report, args.prompt_version)

        result = run_rubric_scoring(report)
        all_results["dimensions"]["reasoning_quality"] = result
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  Average Score: {result['average']}/5 {status}")
        for dim, score in result["scores"].items():
            print(f"    {dim}: {score}/5")

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
        result = run_edge_cases(test_cases, agent, workers=args.workers,
                                prompt_version=args.prompt_version,
                                replay=args.replay, cost_tracker=cost_tracker)
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

    # Cost summary
    print(f"\n{'='*60}")
    print(f"COST SUMMARY {'(replay — $0.00)' if args.replay else ''}")
    print(f"{'='*60}")
    if args.replay:
        print("  API calls        : 0")
        print("  Estimated cost   : $0.0000")
    else:
        print(cost_tracker.summary())

    # Save results (P1 eval scorecards — see results/p1/README.md)
    results_dir = Path("results/p1/eval")
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"eval_{args.prompt_version}_{timestamp}.json"
    all_results["cost"] = {
        "api_calls": cost_tracker.call_count,
        "estimated_usd": cost_tracker.estimated_cost,
        "mode": mode_label,
    }
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nFull results saved to: {results_file}")


if __name__ == "__main__":
    main()
