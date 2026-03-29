"""Session lifecycle — JSON persistence under sessions/."""

import uuid

from fastapi import APIRouter, HTTPException

from backend.api.db import store
from backend.api.models.session import CreateSessionResponse, SessionState

router = APIRouter()


@router.post("", response_model=CreateSessionResponse)
def create_session() -> CreateSessionResponse:
    sid = str(uuid.uuid4())
    state = SessionState(session_id=sid)
    store.save_session(state)
    return CreateSessionResponse(session_id=sid)


@router.get("/{session_id}", response_model=SessionState)
def get_session(session_id: str) -> SessionState:
    state = store.load_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return state
