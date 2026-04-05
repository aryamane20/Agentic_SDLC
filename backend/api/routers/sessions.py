"""Session lifecycle — JSON persistence under sessions/."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.api.db import store
from backend.api.deps import planr_user_id
from backend.api.models.session import (
    CreateSessionResponse,
    SessionState,
    SessionSummary,
)

router = APIRouter()


@router.get("", response_model=list[SessionSummary])
def list_sessions(user_id: str = Depends(planr_user_id)) -> list[SessionSummary]:
    return store.list_session_summaries(user_id)


@router.post("", response_model=CreateSessionResponse)
def create_session() -> CreateSessionResponse:
    """
    Allocate a new chat id only — no JSON file until the first report is saved.
    Avoids a pile of duplicate “empty session” rows in chat history.
    """
    sid = str(uuid.uuid4())
    return CreateSessionResponse(session_id=sid)


@router.get("/{session_id}", response_model=SessionState)
def get_session(
    session_id: str,
    user_id: str = Depends(planr_user_id),
) -> SessionState:
    state = store.load_session(user_id, session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return state
