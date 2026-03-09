"""
Output Schema - Pydantic models for PM Digital Twin output validation.

This module provides Pydantic models that mirror the JSON schema in output_schema.json.
Used by the validator to validate agent output against expected structure + business rules.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum


class ProjectType(str, Enum):
    TYPE_A = "TYPE_A"
    TYPE_B = "TYPE_B"
    TYPE_C = "TYPE_C"
    TYPE_D = "TYPE_D"
    TYPE_E = "TYPE_E"
    TYPE_F = "TYPE_F"


class InputQuality(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SdlcApproach(str, Enum):
    Predictive = "Predictive"
    Adaptive = "Adaptive"
    Hybrid = "Hybrid"


class RiskLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskScore(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskCategory(str, Enum):
    Schedule = "Schedule"
    Resource = "Resource"
    Technical = "Technical"
    Scope = "Scope"
    External = "External"
    Compliance = "Compliance"


class Urgency(str, Enum):
    Before_planning = "Before planning"
    Before_build = "Before build"
    Before_launch = "Before launch"


class AssumptionSource(str, Enum):
    hard_constraint = "hard_constraint"
    soft_constraint = "soft_constraint"
    nfr = "nfr"
    scope = "scope"
    other = "other"


# --- Nested Models ---

class ReportMetadata(BaseModel):
    generated_at: str
    input_quality: InputQuality
    pm_confidence_score: float = Field(ge=0, le=100)
    project_type: ProjectType
    classification_confidence: Optional[InputQuality] = None
    sdlc_approach: SdlcApproach
    sdlc_rationale: Optional[str] = None
    prompt_version: Optional[str] = None


class ProjectUnderstanding(BaseModel):
    primary_goal: str = Field(min_length=10)
    beneficiary: str
    trigger: str
    success_definition: str
    supporting_quotes: Optional[List[str]] = None


class Assumption(BaseModel):
    id: str = Field(pattern=r"^A[0-9]+$")
    what: str = Field(min_length=10)
    why: str = Field(min_length=10)
    pmi_basis: str = Field(min_length=5)
    risk_if_wrong: RiskLevel
    consequence: str = Field(min_length=10)
    source: Optional[AssumptionSource] = None


class CriticalPathSummary(BaseModel):
    sequence: List[str] = Field(min_length=1)
    total_duration_days: float = Field(ge=1)
    zero_slack_tasks: List[str] = Field(min_length=1)
    highest_slack_tasks: Optional[List[str]] = None
    staffing_implication: str = Field(min_length=10)


class Task(BaseModel):
    id: str = Field(pattern=r"^T[0-9]+$")
    name: str = Field(min_length=5)
    phase: int = Field(ge=1, le=5)
    effort_hours: float = Field(ge=1, le=40)
    owner_role: str
    dependencies: List[str]
    risk_flag: bool
    critical_path: bool
    slack_days: int = Field(ge=0)
    definition_of_done: str = Field(min_length=10)


class Phase(BaseModel):
    phase_number: int = Field(ge=1, le=5)
    name: str
    duration_weeks: float = Field(ge=0.5)
    percentage_of_total: float = Field(ge=5, le=50)
    milestones: List[str] = Field(min_length=2)
    tasks: List[Task]


class ProjectPlan(BaseModel):
    total_duration_weeks: float = Field(ge=1)
    buffer_applied_percent: float = Field(ge=0)
    critical_path_summary: CriticalPathSummary
    phases: List[Phase] = Field(min_length=5, max_length=5)


class Risk(BaseModel):
    id: str = Field(pattern=r"^R[0-9]+$")
    category: RiskCategory
    description: str = Field(min_length=20)
    probability: RiskLevel
    impact: RiskLevel
    score: RiskScore
    trigger: str = Field(min_length=10)
    mitigation: str = Field(min_length=10)
    contingency: str = Field(min_length=10)


class StaffingPlanItem(BaseModel):
    role: str
    phase_involvement: List[int]
    total_hours: float = Field(ge=1)
    allocation_percent: float = Field(ge=1, le=80)
    skills_required: List[str] = Field(min_length=1)
    critical_path: bool
    notes: Optional[str] = None


class OpenQuestion(BaseModel):
    priority: int = Field(ge=1, le=5)
    question: str = Field(min_length=10)
    urgency: Urgency
    impact_if_unanswered: str = Field(min_length=10)


class Deduction(BaseModel):
    amount: float
    reason: str


class ViabilityStatus(str, Enum):
    VIABLE = "VIABLE"
    AT_RISK = "AT_RISK"
    NOT_VIABLE = "NOT_VIABLE"
    CANNOT_ASSESS = "CANNOT_ASSESS"


class GapType(str, Enum):
    BUDGET = "BUDGET"
    SCHEDULE = "SCHEDULE"
    BOTH = "BOTH"
    N_A = "N/A"


class ScopingOption(BaseModel):
    option_id: str
    description: str
    impact: str
    tradeoffs: str


class ProjectViability(BaseModel):
    """Project viability assessment - only included when constraints are provided."""
    viability_status: ViabilityStatus
    gap_type: GapType
    gap_amount: str = "N/A"
    scoping_options: Optional[List[ScopingOption]] = None
    
    @field_validator('scoping_options')
    @classmethod
    def scoping_requires_not_viable(cls, v, info):
        """Scoping options only required when status is NOT_VIABLE."""
        # This is a soft validation - we'll handle it in business rules
        return v


class PMConfidenceScore(BaseModel):
    score: float = Field(ge=0, le=100)
    deductions: List[Deduction]
    interpretation: str = Field(min_length=10)


# --- Main Output Model ---

class PMReport(BaseModel):
    """Complete PM Digital Twin report output model."""
    report_metadata: ReportMetadata
    project_understanding: ProjectUnderstanding
    assumption_log: List[Assumption] = Field(min_length=1)
    project_plan: ProjectPlan
    risk_register: List[Risk] = Field(min_length=3)
    staffing_plan: List[StaffingPlanItem] = Field(min_length=1)
    open_questions: List[OpenQuestion] = Field(max_length=5)
    pm_confidence_score: PMConfidenceScore
    
    # Project viability - only included when constraints are provided
    project_viability: Optional[ProjectViability] = None
    
    # Handle parse errors
    parse_error: Optional[bool] = None
    raw_output: Optional[str] = None
