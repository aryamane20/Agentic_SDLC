"""
P3 Prompt Testing Script
Usage:
  python scripts/test_p3_prompts.py --agent use_case --tc tc-01-perfect
  python scripts/test_p3_prompts.py --all --tc tc-01-perfect
  python scripts/test_p3_prompts.py --all --tc tc-01-perfect tc-02-good --save-fixtures

Runs real Haiku API calls. Each agent is tested in pipeline order:
  use_case → intake → planning → risk → staffing → synthesis

Outputs are saved to outputs/p3/agent-runs/ and optionally as
frozen fixtures to inputs/test-cases-p3/fixtures/{agent}/{tc_id}.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv()

from agent.agents import (
    UseCaseAgent, IntakeAgent, PlanningAgent,
    RiskAgent, StaffingAgent, SynthesisAgent,
)
from agent.rag_client import KBRetriever

AGENT_ORDER = ["use_case", "intake", "planning", "risk", "staffing", "synthesis"]

OUTPUT_DIR   = REPO_ROOT / "outputs" / "p3" / "agent-runs"
PIPELINE_DIR = REPO_ROOT / "outputs" / "p3" / "pipeline"
FIXTURE_DIR  = REPO_ROOT / "inputs"  / "test-cases-p3" / "fixtures"
INPUT_DIR_P3 = REPO_ROOT / "inputs"  / "test-cases-p3"
INPUT_DIR_P1 = REPO_ROOT / "inputs"  / "test-cases-p1"


def _load_brief(tc_id: str) -> str:
    for d in [INPUT_DIR_P3, INPUT_DIR_P1]:
        p = d / f"{tc_id}.txt"
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Brief not found for '{tc_id}' in p3 or p1 inputs")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  → saved: {path.relative_to(REPO_ROOT)}")


def run_use_case(brief: str, kb: KBRetriever) -> dict:
    agent = UseCaseAgent()
    context = {"raw_brief": brief}
    t0 = time.time()
    result = agent.run(context=context)
    result["elapsed_seconds"] = round(time.time() - t0, 2)
    return result


def run_intake(brief: str, use_case_artifact: dict, kb: KBRetriever) -> dict:
    agent = IntakeAgent()
    context = {"raw_brief": brief, "use_case_model": use_case_artifact}
    t0 = time.time()
    result = agent.run(context=context)
    result["elapsed_seconds"] = round(time.time() - t0, 2)
    return result


def run_planning(brief: str, use_case_artifact: dict, intake_artifact: dict, kb: KBRetriever) -> dict:
    agent = PlanningAgent()
    project_type = intake_artifact.get("report_metadata", {}).get("project_type")
    context = {
        "raw_brief": brief,
        "structured_brief": intake_artifact,
        "use_case_model": use_case_artifact,
        "_kb_content": kb.get_for_agent("planning", project_type=project_type),
    }
    t0 = time.time()
    result = agent.run(context=context)
    result["elapsed_seconds"] = round(time.time() - t0, 2)
    return result


def run_risk(brief: str, use_case_artifact: dict, intake_artifact: dict,
             planning_artifact: dict, kb: KBRetriever) -> dict:
    agent = RiskAgent()
    context = {
        "raw_brief": brief,
        "structured_brief": intake_artifact,
        "use_case_model": use_case_artifact,
        "project_plan": planning_artifact,
        "_kb_content": kb.get_for_agent("risk"),
    }
    t0 = time.time()
    result = agent.run(context=context)
    result["elapsed_seconds"] = round(time.time() - t0, 2)
    return result


def run_staffing(brief: str, use_case_artifact: dict, intake_artifact: dict,
                 planning_artifact: dict, risk_artifact: dict, kb: KBRetriever) -> dict:
    agent = StaffingAgent()
    context = {
        "raw_brief": brief,
        "structured_brief": intake_artifact,
        "use_case_model": use_case_artifact,
        "project_plan": planning_artifact,
        "risk_register_artifact": risk_artifact,
        "_kb_content": kb.get_for_agent("staffing"),
    }
    t0 = time.time()
    result = agent.run(context=context)
    result["elapsed_seconds"] = round(time.time() - t0, 2)
    return result


def run_synthesis(use_case_artifact: dict, intake_artifact: dict, planning_artifact: dict,
                  risk_artifact: dict, staffing_artifact: dict, kb: KBRetriever) -> dict:
    agent = SynthesisAgent()
    context = {
        "use_case_model": use_case_artifact,
        "structured_brief": intake_artifact,
        "project_plan": planning_artifact,
        "risk_register_artifact": risk_artifact,
        "staffing_plan_artifact": staffing_artifact,
    }
    t0 = time.time()
    result = agent.run(context=context)
    result["elapsed_seconds"] = round(time.time() - t0, 2)
    return result


def run_single_agent(agent_name: str, tc_id: str, save_fixtures: bool) -> None:
    """Run a single agent using prior agents' outputs from saved fixtures."""
    print(f"\n{'='*60}")
    print(f"Agent: {agent_name.upper()}  |  TC: {tc_id}")
    print(f"{'='*60}")

    brief = _load_brief(tc_id)
    kb = KBRetriever()

    def _load_prev(name: str) -> dict:
        p = FIXTURE_DIR / name / f"{tc_id}.json"
        if not p.exists():
            print(f"  [WARN] No fixture for '{name}/{tc_id}' — run earlier agents first")
            return {}
        return json.loads(p.read_text())

    if agent_name == "use_case":
        result = run_use_case(brief, kb)
    elif agent_name == "intake":
        result = run_intake(brief, _load_prev("use_case"), kb)
    elif agent_name == "planning":
        result = run_planning(brief, _load_prev("use_case"), _load_prev("intake"), kb)
    elif agent_name == "risk":
        result = run_risk(brief, _load_prev("use_case"), _load_prev("intake"), _load_prev("planning"), kb)
    elif agent_name == "staffing":
        result = run_staffing(brief, _load_prev("use_case"), _load_prev("intake"),
                              _load_prev("planning"), _load_prev("risk"), kb)
    elif agent_name == "synthesis":
        result = run_synthesis(_load_prev("use_case"), _load_prev("intake"),
                               _load_prev("planning"), _load_prev("risk"), _load_prev("staffing"), kb)
    else:
        print(f"Unknown agent: {agent_name}")
        return

    _print_result(agent_name, result)

    out = {"agent": agent_name, "tc": tc_id, **result}
    _save(OUTPUT_DIR / f"{agent_name}_{tc_id}_{_ts()}.json", out)

    if save_fixtures:
        _save(FIXTURE_DIR / agent_name / f"{tc_id}.json", result["artifact"])


def run_full_pipeline(tc_id: str, save_fixtures: bool) -> None:
    """Run all 6 agents in sequence, passing outputs through the pipeline."""
    print(f"\n{'='*60}")
    print(f"FULL PIPELINE  |  TC: {tc_id}")
    print(f"{'='*60}")

    brief = _load_brief(tc_id)
    kb = KBRetriever()
    pipeline_start = time.time()
    total_tokens = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}

    def _tally(r: dict):
        total_tokens["input"]          += r.get("input_tokens", 0)
        total_tokens["output"]         += r.get("output_tokens", 0)
        total_tokens["cache_read"]     += r.get("cache_read_tokens", 0)
        total_tokens["cache_creation"] += r.get("cache_creation_tokens", 0)

    def _step(name: str, result: dict) -> dict:
        _print_result(name, result)
        _tally(result)
        out = {"agent": name, "tc": tc_id, **result}
        _save(OUTPUT_DIR / f"{name}_{tc_id}_{_ts()}.json", out)
        if save_fixtures and not result.get("parse_failed"):
            _save(FIXTURE_DIR / name / f"{tc_id}.json", result["artifact"])
        return result["artifact"]

    uc_a  = _step("use_case", run_use_case(brief, kb))
    in_a  = _step("intake",   run_intake(brief, uc_a, kb))
    pl_a  = _step("planning", run_planning(brief, uc_a, in_a, kb))
    ri_a  = _step("risk",     run_risk(brief, uc_a, in_a, pl_a, kb))
    st_a  = _step("staffing", run_staffing(brief, uc_a, in_a, pl_a, ri_a, kb))
    sy_a  = _step("synthesis",run_synthesis(uc_a, in_a, pl_a, ri_a, st_a, kb))

    elapsed = round(time.time() - pipeline_start, 2)
    print(f"\n{'─'*60}")
    print(f"Pipeline complete in {elapsed}s")
    print(f"Total tokens — input: {total_tokens['input']}  output: {total_tokens['output']}  "
          f"cache_read: {total_tokens['cache_read']}  cache_creation: {total_tokens['cache_creation']}")

    pipeline_out = {
        "tc": tc_id,
        "elapsed_seconds": elapsed,
        "token_tally": total_tokens,
        "artifacts": {
            "use_case": uc_a, "intake": in_a, "planning": pl_a,
            "risk": ri_a, "staffing": st_a, "synthesis": sy_a,
        },
    }
    _save(PIPELINE_DIR / f"pipeline_{tc_id}_{_ts()}.json", pipeline_out)


def _print_result(name: str, result: dict) -> None:
    status = "FAILED" if result.get("parse_failed") else "OK"
    color  = "\033[91m" if result.get("parse_failed") else "\033[92m"
    reset  = "\033[0m"
    print(f"\n{color}[{status}]{reset} {name.upper()}  "
          f"({result.get('elapsed_seconds', '?')}s, "
          f"in={result.get('input_tokens',0)} out={result.get('output_tokens',0)} "
          f"attempts={result.get('attempts',1)})")

    artifact = result.get("artifact", {})
    if result.get("parse_failed"):
        print(f"  parse_error: {artifact.get('parse_error')}")
        raw = result.get("raw_output", "")[:300]
        print(f"  raw (first 300): {raw!r}")
    else:
        # Print a brief summary per agent
        if name == "use_case":
            print(f"  actors={len(artifact.get('actors',[]))}  "
                  f"use_cases={len(artifact.get('use_cases',[]))}  "
                  f"quality={artifact.get('input_quality_signal')}")
        elif name == "intake":
            print(f"  project_type={artifact.get('report_metadata',{}).get('project_type')}  "
                  f"assumptions={len(artifact.get('assumption_log',[]))}  "
                  f"sdlc={artifact.get('report_metadata',{}).get('sdlc_approach')}")
        elif name == "planning":
            plan = artifact.get("project_plan", {})
            phases = plan.get("phases", [])
            print(f"  duration={plan.get('total_duration_weeks')}w  "
                  f"phases={len(phases)}  "
                  f"p5%={next((p.get('percentage_of_total') for p in phases if p.get('phase_number')==5), '?')}")
        elif name == "risk":
            risks = artifact.get("risk_register", [])
            scores = [r.get("score") for r in risks]
            print(f"  risks={len(risks)}  "
                  f"CRITICAL={scores.count('CRITICAL')}  HIGH={scores.count('HIGH')}  "
                  f"cp_flags={len(artifact.get('critical_path_risk_flags',[]))}")
        elif name == "staffing":
            roles = artifact.get("staffing_plan", [])
            over_80 = [r.get("role") for r in roles if (r.get("allocation_percent") or 0) > 80]
            score = artifact.get("pm_confidence_score", {})
            print(f"  roles={len(roles)}  "
                  f"confidence={score.get('score')}  "
                  f"over_80%={over_80 or 'none'}")
        elif name == "synthesis":
            issues = artifact.get("consistency_issues", [])
            score = artifact.get("pm_confidence_score", {})
            print(f"  consistency_issues={len(issues)}  "
                  f"corrections={len(artifact.get('corrections_applied',[]))}  "
                  f"staffing_corrections={len(artifact.get('staffing_corrections',[]))}  "
                  f"added_questions={len(artifact.get('added_open_questions',[]))}  "
                  f"confidence={score.get('score') if isinstance(score,dict) else score}")


def main() -> None:
    parser = argparse.ArgumentParser(description="P3 prompt testing tool")
    parser.add_argument("--agent", choices=AGENT_ORDER,
                        help="Run a single agent (requires prior fixtures)")
    parser.add_argument("--all", action="store_true",
                        help="Run full pipeline (all 6 agents in sequence)")
    parser.add_argument("--tc", nargs="+", default=["tc-01-perfect"],
                        help="Test case ID(s), e.g. tc-01-perfect tc-02-good")
    parser.add_argument("--save-fixtures", action="store_true",
                        help="Save artifacts as frozen fixtures for replay tests")
    args = parser.parse_args()

    if not args.agent and not args.all:
        parser.print_help()
        sys.exit(1)

    for tc_id in args.tc:
        if args.all:
            run_full_pipeline(tc_id, save_fixtures=args.save_fixtures)
        else:
            run_single_agent(args.agent, tc_id, save_fixtures=args.save_fixtures)


if __name__ == "__main__":
    main()
