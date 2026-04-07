"""Shared helpers for P2 fixture-based tests."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# All P2 inputs (briefs + frozen report JSON) live under inputs/test-cases-p2/
P2_FIXTURES = REPO_ROOT / "inputs" / "test-cases-p2" / "fixtures"
FIXTURES = P2_FIXTURES  # alias for test modules using FIXTURES / "gates"


def load_report_fixture(*parts: str) -> dict:
    """Load a JSON report from inputs/test-cases-p2/fixtures/{parts...}."""
    path = P2_FIXTURES.joinpath(*parts)
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))
