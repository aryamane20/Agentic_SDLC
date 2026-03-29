"""
PM Digital Twin — FastAPI backend (Project 2).

Run from repository root (so agent/, prompts/, knowledge-base/ resolve):
  pip install -r requirements.txt -r backend/requirements.txt
  uvicorn backend.api.main:app --reload --port 8000

Stack: FastAPI + Uvicorn (docs/ARCHITECTURE.md §6).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import gates, refine, reports, sessions

app = FastAPI(
    title="PM Digital Twin API",
    description="HITL approval gates + session persistence wrapping PMAgent",
    version="0.1.0",
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(gates.router, prefix="/gates", tags=["gates"])
app.include_router(refine.router, prefix="", tags=["refine"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
