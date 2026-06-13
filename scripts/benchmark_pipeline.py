"""
scripts/benchmark_pipeline.py

Times each node in the P3 pipeline against a real brief.
Uses real Haiku API calls — costs tokens.

Usage:
    python scripts/benchmark_pipeline.py                      # uses tc-01-perfect
    python scripts/benchmark_pipeline.py --tc tc-02-good
    python scripts/benchmark_pipeline.py --brief "Build a CRM for our sales team"

Output: per-node wall time + total, with a note on the sequential overhead
from the planning_node → risk_node split (Option A).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv()

from agent.rag_client import KBRetriever
from agent.agents import (
    UseCaseAgent, IntakeAgent, PlanningAgent,
    RiskAgent, StaffingAgent, SynthesisAgent,
)

INPUT_DIR_P3 = REPO_ROOT / "inputs" / "test-cases-p3"
INPUT_DIR_P1 = REPO_ROOT / "inputs" / "test-cases-p1"

_SEP = "─" * 60


def _load_brief(tc_id: str) -> str:
    for d in [INPUT_DIR_P3, INPUT_DIR_P1]:
        p = d / f"{tc_id}.txt"
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Brief not found for '{tc_id}'")


def _fmt(seconds: float) -> str:
    return f"{seconds:.2f}s"


async def run_benchmark(brief: str) -> None:
    kb = KBRetriever()
    timings: dict[str, float] = {}
    tokens: dict[str, dict] = {}

    print(f"\n{_SEP}")
    print("PLANR P3 Pipeline Benchmark — Option A (sequential planning → risk)")
    print(_SEP)

    # ── use_case ──────────────────────────────────────────────────────────────
    print("\n[1/6] use_case_node ...", end=" ", flush=True)
    t0 = time.perf_counter()
    uc_result = await UseCaseAgent().run_async(context={"raw_brief": brief})
    timings["use_case"] = time.perf_counter() - t0
    tokens["use_case"] = uc_result
    uc_artifact = uc_result["artifact"]
    print(_fmt(timings["use_case"]))

    # ── intake ────────────────────────────────────────────────────────────────
    print("[2/6] intake_node    ...", end=" ", flush=True)
    t0 = time.perf_counter()
    intake_result = await IntakeAgent().run_async(context={
        "raw_brief": brief,
        "use_case_model": uc_artifact,
    })
    timings["intake"] = time.perf_counter() - t0
    tokens["intake"] = intake_result
    intake_artifact = intake_result["artifact"]
    project_type = intake_artifact.get("report_metadata", {}).get("project_type")
    print(_fmt(timings["intake"]))

    quality = uc_artifact.get("input_quality_signal", "?")
    if quality == "LOW":
        print(f"\n⚠  Gate fired (quality={quality}). Pipeline stopped at intake.")
        _print_summary(timings, tokens, gate_fired=True)
        return

    # ── planning (sequential — runs first so risk sees the WBS) ───────────────
    print("[3/6] planning_node  ...", end=" ", flush=True)
    t0 = time.perf_counter()
    planning_result = await PlanningAgent().run_async(context={
        "structured_brief": intake_artifact,
        "use_case_model": uc_artifact,
        "_kb_content": kb.get_for_agent("planning", project_type=project_type),
    })
    timings["planning"] = time.perf_counter() - t0
    tokens["planning"] = planning_result
    planning_artifact = planning_result["artifact"]
    print(_fmt(timings["planning"]))

    # ── risk (sequential — receives full planning artifact) ───────────────────
    print("[4/6] risk_node      ...", end=" ", flush=True)
    t0 = time.perf_counter()
    risk_result = await RiskAgent().run_async(context={
        "structured_brief": intake_artifact,
        "use_case_model": uc_artifact,
        "project_plan": planning_artifact,   # ← non-empty after Option A
        "_kb_content": kb.get_for_agent("risk", project_type=project_type),
    })
    timings["risk"] = time.perf_counter() - t0
    tokens["risk"] = risk_result
    risk_artifact = risk_result["artifact"]
    print(_fmt(timings["risk"]))

    # ── staffing ──────────────────────────────────────────────────────────────
    print("[5/6] staffing_node  ...", end=" ", flush=True)
    t0 = time.perf_counter()
    staffing_result = await StaffingAgent().run_async(context={
        "structured_brief": intake_artifact,
        "use_case_model": uc_artifact,
        "project_plan": planning_artifact,
        "risk_register_artifact": risk_artifact,
        "_kb_content": kb.get_for_agent("staffing", project_type=project_type),
    })
    timings["staffing"] = time.perf_counter() - t0
    tokens["staffing"] = staffing_result
    staffing_artifact = staffing_result["artifact"]
    print(_fmt(timings["staffing"]))

    # ── synthesis ─────────────────────────────────────────────────────────────
    print("[6/6] synthesis_node ...", end=" ", flush=True)
    t0 = time.perf_counter()
    synthesis_result = await SynthesisAgent().run_async(context={
        "use_case_model": uc_artifact,
        "structured_brief": intake_artifact,
        "project_plan": planning_artifact,
        "risk_register_artifact": risk_artifact,
        "staffing_plan_artifact": staffing_artifact,
    })
    timings["synthesis"] = time.perf_counter() - t0
    tokens["synthesis"] = synthesis_result
    print(_fmt(timings["synthesis"]))

    _print_summary(timings, tokens, gate_fired=False)


def _print_summary(
    timings: dict[str, float],
    tokens: dict[str, dict],
    gate_fired: bool,
) -> None:
    print(f"\n{_SEP}")
    print("TIMING BREAKDOWN")
    print(_SEP)

    total = sum(timings.values())
    for node, t in timings.items():
        pct = (t / total * 100) if total else 0
        tok_in  = tokens[node].get("input_tokens", 0)
        tok_out = tokens[node].get("output_tokens", 0)
        print(f"  {node:<12} {_fmt(t):>7}  ({pct:4.1f}%)   {tok_in:>5} in / {tok_out:>4} out tokens")

    print(f"  {'TOTAL':<12} {_fmt(total):>7}")

    if not gate_fired and "planning" in timings and "risk" in timings:
        sequential_cost = timings["planning"] + timings["risk"]
        parallel_estimate = max(timings["planning"], timings["risk"])
        overhead = sequential_cost - parallel_estimate
        print(f"\nOption A overhead vs parallel planning+risk:")
        print(f"  Sequential (planning + risk): {_fmt(sequential_cost)}")
        print(f"  Parallel estimate (max):      {_fmt(parallel_estimate)}")
        print(f"  Added latency:                +{_fmt(overhead)}")

    print(_SEP)

    if not gate_fired:
        total_in  = sum(r.get("input_tokens", 0) for r in tokens.values())
        total_out = sum(r.get("output_tokens", 0) for r in tokens.values())
        total_cr  = sum(r.get("cache_read_tokens", 0) for r in tokens.values())
        print(f"Token totals:  {total_in} input  /  {total_out} output  /  {total_cr} cache_read")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the P3 pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tc", default="tc-01-perfect", help="Test case ID (default: tc-01-perfect)")
    group.add_argument("--brief", help="Inline brief text instead of loading from file")
    args = parser.parse_args()

    brief = args.brief if args.brief else _load_brief(args.tc)
    if not args.brief:
        print(f"Brief: {args.tc}")

    asyncio.run(run_benchmark(brief))


if __name__ == "__main__":
    main()
