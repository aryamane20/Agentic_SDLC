"""JSON file persistence under sessions/ — zero-setup MVP per ARCHITECTURE.md."""

import json
import tempfile
from pathlib import Path
from typing import Optional

from backend.api.models.session import SessionState, SessionSummary

SESSIONS_DIR = Path("sessions")
_USERS = "_users"


def _normalize_user(user_id: str) -> str:
    t = (user_id or "").strip() or "anonymous"
    return t


def _user_sessions_dir(user_id: str) -> Path:
    uid = _normalize_user(user_id)
    d = SESSIONS_DIR / _USERS / uid
    d.mkdir(parents=True, exist_ok=True)
    return d


def _session_path(user_id: str, session_id: str) -> Path:
    safe = session_id.replace("/", "").replace("..", "")
    return _user_sessions_dir(user_id) / f"{safe}.json"


def _legacy_flat_path(session_id: str) -> Path:
    safe = session_id.replace("/", "").replace("..", "")
    return SESSIONS_DIR / f"{safe}.json"


def ensure_sessions_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def load_session(user_id: str, session_id: str) -> Optional[SessionState]:
    path = _session_path(user_id, session_id)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return SessionState.model_validate(data)
    if _normalize_user(user_id) == "anonymous" and _legacy_flat_path(
        session_id
    ).exists():
        data = json.loads(
            _legacy_flat_path(session_id).read_text(encoding="utf-8")
        )
        return SessionState.model_validate(data)
    return None


def save_session(user_id: str, state: SessionState) -> None:
    ensure_sessions_dir()
    path = _session_path(user_id, state.session_id)
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


def _summaries_from_paths(
    paths: list[Path],
) -> list[tuple[float, SessionSummary]]:
    rows: list[tuple[float, SessionSummary]] = []
    for path in paths:
        try:
            st = path.stat().st_mtime
            state = SessionState.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        n = len(state.reports)
        if n == 0:
            continue
        raw = (state.reports[-1].brief or "").replace("\n", " ").strip()
        preview = (raw[:120] + "…") if len(raw) > 120 else raw or "(no brief text)"
        rows.append(
            (
                st,
                SessionSummary(
                    session_id=state.session_id,
                    report_count=n,
                    updated_at=st,
                    preview=preview,
                ),
            )
        )
    return rows


def list_session_summaries(user_id: str, limit: int = 50) -> list[SessionSummary]:
    """
    Newest first by file mtime. Plans with no saved reports are skipped.
    Legacy: namespace 'anonymous' also reads top-level sessions/*.json.
    """
    ensure_sessions_dir()
    paths: list[Path] = list(_user_sessions_dir(user_id).glob("*.json"))
    if _normalize_user(user_id) == "anonymous":
        paths.extend(p for p in SESSIONS_DIR.glob("*.json") if p.is_file())
    rows = _summaries_from_paths(paths)
    rows.sort(key=lambda x: x[0], reverse=True)
    seen: set[str] = set()
    out: list[SessionSummary] = []
    for _, s in rows:
        if s.session_id in seen:
            continue
        seen.add(s.session_id)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def find_report_session(
    user_id: str, report_id: str
) -> Optional[tuple[str, int]]:
    """
    Scan session files for report_id under this user's namespace.
    anonymous also scans legacy flat sessions/*.json.
    """
    ensure_sessions_dir()
    paths: list[Path] = list(_user_sessions_dir(user_id).glob("*.json"))
    if _normalize_user(user_id) == "anonymous":
        paths.extend(p for p in SESSIONS_DIR.glob("*.json") if p.is_file())
    seen_path: set[str] = set()
    for path in paths:
        rp = str(path.resolve())
        if rp in seen_path:
            continue
        seen_path.add(rp)
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
