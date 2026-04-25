"""DELETE /sessions/{id} — remove persisted session for current user."""

import json
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

import backend.api.db.store as store_module
from backend.api.main import app
from backend.api.models.gate import GateState
from backend.api.models.session import ReportEntry, SessionState

client = TestClient(app)

HEADERS = {"X-Planr-User": "delete-test-user"}


def _write_session(sessions_dir: Path, user_id: str, state: SessionState) -> None:
    uid = user_id.strip() or "anonymous"
    user_dir = sessions_dir / "_users" / uid
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f"{state.session_id}.json"
    payload = state.model_dump(mode="json")
    fd, tmp = tempfile.mkstemp(dir=user_dir, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, indent=2))
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _state(sid: str, rid: str) -> SessionState:
    entry = ReportEntry(
        report_id=rid,
        brief="Test brief",
        report={"pm_confidence_score": {"score": 80}},
        gate=GateState(fired=False, reasons=[], decision=None),
        report_revision=1,
    )
    return SessionState(session_id=sid, reports=[entry])


def test_delete_session_removes_file_and_get_returns_404(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "SESSIONS_DIR", tmp_path)

    sid, rid = "ses-del-001", "rpt-del-001"
    _write_session(tmp_path, "delete-test-user", _state(sid, rid))
    user_file = (
        tmp_path / "_users" / "delete-test-user" / f"{sid}.json"
    )
    assert user_file.is_file()

    resp = client.delete(f"/sessions/{sid}", headers=HEADERS)
    assert resp.status_code == 204
    assert not user_file.exists()

    resp2 = client.get(f"/sessions/{sid}", headers=HEADERS)
    assert resp2.status_code == 404


def test_delete_session_other_user_404s(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "SESSIONS_DIR", tmp_path)

    sid, rid = "ses-del-002", "rpt-del-002"
    _write_session(tmp_path, "other-user", _state(sid, rid))
    other_file = tmp_path / "_users" / "other-user" / f"{sid}.json"
    assert other_file.is_file()

    resp = client.delete(f"/sessions/{sid}", headers=HEADERS)
    assert resp.status_code == 404
    assert other_file.is_file()
    assert json.loads(other_file.read_text(encoding="utf-8"))["session_id"] == sid


def test_delete_missing_session_404(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "SESSIONS_DIR", tmp_path)
    resp = client.delete("/sessions/00000000-0000-0000-0000-000000000000", headers=HEADERS)
    assert resp.status_code == 404
