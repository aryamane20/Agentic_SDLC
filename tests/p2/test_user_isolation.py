"""User isolation: User B cannot access User A's sessions or reports.

Uses real file I/O via monkeypatch on store.SESSIONS_DIR (no mocks).
"""

import json

from fastapi.testclient import TestClient

import backend.api.db.store as store_module
from backend.api.main import app
from backend.api.models.gate import GateState
from backend.api.models.session import ReportEntry, SessionState

client = TestClient(app)

HEADERS_A = {"X-Planr-User": "isolation-user-a"}
HEADERS_B = {"X-Planr-User": "isolation-user-b"}


def _write_session(sessions_dir, user_id: str, state: SessionState) -> None:
    """Write a session JSON directly into the tmp sessions dir."""
    import tempfile
    from pathlib import Path

    uid = user_id.strip() or "anonymous"
    user_dir = sessions_dir / "_users" / uid
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f"{state.session_id}.json"
    payload = state.model_dump(mode="json")
    fd, tmp = tempfile.mkstemp(dir=user_dir, prefix=f".{path.name}.", suffix=".tmp")
    try:
        import os
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, indent=2))
        Path(tmp).replace(path)
    except BaseException:
        from pathlib import Path as P
        P(tmp).unlink(missing_ok=True)
        raise


def _make_state(session_id: str, report_id: str) -> SessionState:
    entry = ReportEntry(
        report_id=report_id,
        brief="Confidential initiative",
        report={"pm_confidence_score": {"score": 80}},
        gate=GateState(fired=False, reasons=[], decision=None),
        report_revision=1,
    )
    return SessionState(session_id=session_id, reports=[entry])


def test_user_b_cannot_read_user_a_session(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "SESSIONS_DIR", tmp_path)

    state_a = _make_state("ses-iso-001", "rpt-iso-001")
    _write_session(tmp_path, "isolation-user-a", state_a)

    resp = client.get("/sessions/ses-iso-001", headers=HEADERS_B)
    assert resp.status_code == 404


def test_user_b_cannot_read_user_a_report(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "SESSIONS_DIR", tmp_path)

    state_a = _make_state("ses-iso-002", "rpt-iso-002")
    _write_session(tmp_path, "isolation-user-a", state_a)

    resp = client.get("/reports/rpt-iso-002", headers=HEADERS_B)
    assert resp.status_code == 404


def test_user_b_session_list_is_empty_when_only_user_a_has_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "SESSIONS_DIR", tmp_path)

    state_a = _make_state("ses-iso-003", "rpt-iso-003")
    _write_session(tmp_path, "isolation-user-a", state_a)

    resp = client.get("/sessions", headers=HEADERS_B)
    assert resp.status_code == 200
    assert resp.json() == []
