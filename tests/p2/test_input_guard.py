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


# Golden-dataset happy_path briefs that previously slipped through `input_guard`
# as `brief_missing/no_project_signal`. The two regressions:
#   - hp-02 (scenario-b-low-confidence): "tracking stuff", "app?", "Timeline is soon"
#     — punctuation-glued tokens ("app?") killed the _PROJECT_SIGNALS lookup.
#   - hp-06 (tc-04-vague): "We need to improve how we track projects."
#     — neither "track" nor "projects" was in _PROJECT_SIGNALS.
# Keep these as explicit asserts so a future signals/tokenizer change can't
# silently re-break the happy path.
HAPPY_PATH_BRIEFS = {
    "hp-02": "inputs/test-cases-p2/scenario-b-low-confidence/brief.txt",
    "hp-06": "inputs/test-cases/tc-04-vague.txt",
}


@pytest.mark.parametrize("case_id,brief_path", sorted(HAPPY_PATH_BRIEFS.items()))
def test_happy_path_briefs_pass_input_guard(case_id: str, brief_path: str) -> None:
    repo_root = Path(__file__).parent.parent.parent
    text = (repo_root / brief_path).read_text()
    verdict = classify_input(text)
    assert verdict.verdict == "OK", (
        f"{case_id}: expected verdict=OK, got {verdict.verdict!r} "
        f"(reason_code={verdict.reason_code!r}). Brief: {text!r}"
    )
    assert verdict.reason_code is None
