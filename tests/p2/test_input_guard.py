import json
from pathlib import Path

import pytest

from backend.api.services.input_guard import classify_input

INTAKE_DIR = Path(__file__).parent.parent.parent / "inputs" / "test-cases-p2" / "intake"
EXPECTATIONS: dict = json.loads((INTAKE_DIR / "expectations.json").read_text())


@pytest.mark.parametrize("fixture_name", sorted(EXPECTATIONS.keys()))
def test_intake_contract(fixture_name: str) -> None:
    text = (INTAKE_DIR / f"{fixture_name}.txt").read_text()
    verdict = classify_input(text)
    exp = EXPECTATIONS[fixture_name]
    assert verdict.verdict == exp["verdict"], (
        f"{fixture_name}: expected verdict={exp['verdict']!r}, got {verdict.verdict!r} "
        f"(reason_code={verdict.reason_code!r})"
    )
    if exp["reason_code"]:
        assert verdict.reason_code == exp["reason_code"], (
            f"{fixture_name}: expected reason_code={exp['reason_code']!r}, got {verdict.reason_code!r}"
        )
