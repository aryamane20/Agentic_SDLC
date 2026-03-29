"""Persisted session shape — aligns with docs/ARCHITECTURE.md MVP JSON store."""

from typing import Any, Optional

from pydantic import BaseModel, Field

from backend.api.models.gate import GateState


class RefinementRecord(BaseModel):
    feedback: str
    report: dict[str, Any]
    gate: GateState


class ReportEntry(BaseModel):
    report_id: str
    brief: str
    report: dict[str, Any]
    gate: GateState
    refinements: list[RefinementRecord] = Field(default_factory=list)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    tokens_used: Optional[int] = None


class SessionState(BaseModel):
    session_id: str
    reports: list[ReportEntry] = Field(default_factory=list)


class CreateSessionResponse(BaseModel):
    session_id: str
