"""API request/response models for gates and refinement."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class GateState(BaseModel):
    """Result of evaluating approval rules on a report."""

    fired: bool
    reasons: list[str] = Field(default_factory=list)
    decision: Optional[Literal["approve", "reject"]] = None


class GateDecisionRequest(BaseModel):
    session_id: str
    decision: Literal["approve", "reject"]
    #: When set, must match `ReportEntry.report_revision` or the server returns 409 (concurrent edit).
    expected_revision: Optional[int] = Field(default=None, ge=1)


class RefineRequest(BaseModel):
    session_id: str
    feedback: str = Field(..., min_length=1)
    #: Scenario B — new constraint in feedback; only lock project_understanding; allow assumption_log to change.
    update_brief: bool = False
    #: When set, must match `ReportEntry.report_revision` or the server returns 409 (concurrent refine).
    expected_revision: Optional[int] = Field(default=None, ge=1)


class GenerateReportRequest(BaseModel):
    session_id: str
    #: Freeform description; may be empty if `prd_text` carries requirements.
    brief: str = ""
    #: Extracted text from an uploaded PRD (.txt / .md / .pdf / .docx).
    prd_text: Optional[str] = None
    use_cache: bool = True
    prompt_version: Optional[str] = None

    @model_validator(mode="after")
    def brief_or_prd(self) -> "GenerateReportRequest":
        b = (self.brief or "").strip()
        p = (self.prd_text or "").strip()
        if not b and not p:
            raise ValueError("Provide a brief and/or PRD content")
        return self
