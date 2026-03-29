"""JSON file persistence under sessions/ — zero-setup MVP per ARCHITECTURE.md."""

import json
import tempfile
from pathlib import Path
from typing import Optional

from backend.api.models.session import SessionState

SESSIONS_DIR = Path("sessions")


def _session_path(session_id: str) -> Path:
    safe = session_id.replace("/", "").replace("..", "")
    return SESSIONS_DIR / f"{safe}.json"


def ensure_sessions_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def load_session(session_id: str) -> Optional[SessionState]:
    path = _session_path(session_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SessionState.model_validate(data)


def save_session(state: SessionState) -> None:
    ensure_sessions_dir()
    path = _session_path(state.session_id)
    payload = state.model_dump(mode="json")
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(text)
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def find_report_session(report_id: str) -> Optional[tuple[str, int]]:
    """
    Scan session files for report_id. Returns (session_id, report_index) or None.
    MVP linear scan; replace with index if session count grows.
    """
    ensure_sessions_dir()
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            state = SessionState.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except (json.JSONDecodeError, ValueError):
            continue
        for i, rep in enumerate(state.reports):
            if rep.report_id == report_id:
                return state.session_id, i
    return None
