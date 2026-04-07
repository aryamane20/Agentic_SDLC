"""
Dimension 1 — gate evaluation on file-backed report JSON (no API).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.api.services.approval_gate import evaluate_gate

from tests.p2.conftest import FIXTURES

GATES_DIR = FIXTURES / "gates"


def _gate_cases():
    """id, expect_fired, reason_substr (optional matcher on reasons, lower-case contains)."""
    return [
        ("clean_no_gate.json", False, None),
        ("low_confidence.json", True, "confidence"),
        ("critical_risk.json", True, "critical"),
    ]


@pytest.mark.parametrize("filename,expect_fired,reason_substr", _gate_cases())
def test_evaluate_gate_on_json_fixture(filename, expect_fired, reason_substr):
    path = GATES_DIR / filename
    report = json.loads(path.read_text(encoding="utf-8"))
    gate = evaluate_gate(report)
    assert gate.fired is expect_fired
    if reason_substr:
        joined = " ".join(gate.reasons).lower()
        assert reason_substr in joined
