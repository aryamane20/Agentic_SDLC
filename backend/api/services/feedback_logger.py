"""Append gate decisions to logs/gate_decisions.jsonl."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_PATH = Path("logs") / "gate_decisions.jsonl"


def log_gate_decision(
    *,
    session_id: str,
    report_id: str,
    decision: str,
    gate_fired: bool,
    reasons: list[str],
    extra: dict[str, Any] | None = None,
) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "report_id": report_id,
        "decision": decision,
        "gate_fired": gate_fired,
        "reasons": reasons,
    }
    if extra:
        row["extra"] = extra
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
