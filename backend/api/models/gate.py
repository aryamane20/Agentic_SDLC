"""API request/response models for gates and refinement."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GateState(BaseModel):
    """Result of evaluating approval rules on a report."""

    fired: bool
    reasons: list[str] = Field(default_factory=list)
    decision: Optional[Literal["approve", "reject"]] = None


class GateDecisionRequest(BaseModel):
    session_id: str
    decision: Literal["approve", "reject"]


class RefineRequest(BaseModel):
    session_id: str
    feedback: str = Field(..., min_length=1)


class GenerateReportRequest(BaseModel):
    session_id: str
    brief: str = Field(..., min_length=1)
    use_cache: bool = True
    prompt_version: Optional[str] = None
