#!/usr/bin/env python3
"""
P2 workflow scenario loader — lists scenarios and prints refinement steps.

Dry-run: lists scenarios and prints brief path + refinement text.
Live E2E: use scripts/run_p2_e2e.py (see results/p2/e2e/README.md).
--execute prints that pointer (this script stays read-only for inputs).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P2_DIR = ROOT / "inputs" / "test-cases-p2"


def _load_manifests() -> list[tuple[Path, dict]]:
    out: list[tuple[Path, dict]] = []
    if not P2_DIR.is_dir():
        return out
    for d in sorted(P2_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        mf = d / "manifest.json"
        if mf.is_file():
            with open(mf, encoding="utf-8") as f:
                out.append((d, json.load(f)))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="P2 HITL scenario helper (dry-run by default)")
    parser.add_argument(
        "--scenario",
        metavar="ID",
        help="Manifest id (e.g. p2-scenario-a-happy-path) or folder name (e.g. scenario-a-happy-path)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Print how to run scripts/run_p2_e2e.py (this file does not call the API)",
    )
    args = parser.parse_args()

    if args.execute:
        print(
            "Use the E2E runner (starts the API separately, then):\n"
            "  python scripts/run_p2_e2e.py --scenario <folder-or-id> --mode manifest|file|interactive\n"
            "See results/p2/e2e/README.md and inputs/test-cases-p2/e2e_feedback/README.md",
            file=sys.stderr,
        )
        sys.exit(2)

    manifests = _load_manifests()
    if not manifests:
        print(f"No scenarios found under {P2_DIR}", file=sys.stderr)
        sys.exit(1)

    if args.scenario:
        picked = None
        for folder, data in manifests:
            if data.get("id") == args.scenario or folder.name == args.scenario:
                picked = (folder, data)
                break
        if not picked:
            print(f"Scenario not found: {args.scenario}", file=sys.stderr)
            sys.exit(1)
        folder, data = picked
        brief = folder / "brief.txt"
        print(f"Id         : {data.get('id')}")
        print(f"Title      : {data.get('title')}")
        print(f"Folder     : {folder.relative_to(ROOT)}")
        print(f"Brief file : {brief.relative_to(ROOT)}")
        print(f"Goal       : {data.get('goal')}")
        print("\nRefinement rounds (apply in order; re-check gate after each):\n")
        for i, rnd in enumerate(data.get("refinement_rounds") or [], 1):
            print(f"  {i}. [{rnd.get('label')}]")
            print(f"     {rnd.get('feedback', '').strip()}\n")
        expected = data.get("expected") or {}
        if expected:
            print("Expected (soft — LLM variance):\n", json.dumps(expected, indent=2))
        return

    print("P2 scenarios (use --scenario <id-or-folder> for details):\n")
    for folder, data in manifests:
        print(f"  {data.get('id')}  —  {folder.name}")
    print(f"\nRoot: {P2_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
