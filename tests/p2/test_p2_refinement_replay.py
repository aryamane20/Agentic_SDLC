"""
Dimension 2 — refinement replay: gate state on frozen JSON snapshots.

These JSON files are minimal dicts with only the fields `evaluate_gate` consults.
They stand in for "report after generate" vs "report after refine N" until you
replace them with full PMReport exports from real runs (optional).

Expected gate outcomes live in each folder's replay_expectations.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.api.services.approval_gate import evaluate_gate

from tests.p2.conftest import P2_FIXTURES

REFINEMENT_ROOT = P2_FIXTURES / "refinement"

# Snapshot stem must match filename: initial.json, after_round_01.json, after_round_02.json
_SNAPSHOT_KEYS = ("initial", "after_round_01", "after_round_02")


def _scenarios_with_replay():
    if not REFINEMENT_ROOT.is_dir():
        return []
    out = []
    for d in sorted(REFINEMENT_ROOT.iterdir()):
        if (
            d.is_dir()
            and not d.name.startswith(".")
            and (d / "replay_expectations.json").is_file()
            and (d / "initial.json").is_file()
        ):
            out.append(d)
    return out


@pytest.mark.parametrize("scenario_dir", _scenarios_with_replay())
def test_refinement_replay_gate_matches_expectations(scenario_dir: Path):
    raw = (scenario_dir / "replay_expectations.json").read_text(encoding="utf-8")
    expectations = json.loads(raw)

    for key in _SNAPSHOT_KEYS:
        if key not in expectations:
            continue
        json_path = scenario_dir / f"{key}.json"
        if not json_path.is_file():
            continue
        report = json.loads(json_path.read_text(encoding="utf-8"))
        gate = evaluate_gate(report)
        want = expectations[key]["fired"]
        assert gate.fired is want, (
            f"{scenario_dir.name}/{key}.json: expected fired={want}, "
            f"got {gate.fired}, reasons={gate.reasons}"
        )
