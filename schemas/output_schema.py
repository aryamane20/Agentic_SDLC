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
    Integration = "Integration"
    Compliance = "Compliance"
    Budget = "Budget"


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
    generated_at: Optional[str] = None
    input_quality: Optional[InputQuality] = None
    project_type: Optional[ProjectType] = None
    classification_confidence: Optional[InputQuality] = None
    sdlc_approach: Optional[SdlcApproach] = None
    sdlc_rationale: Optional[str] = None
    prompt_version: Optional[str] = None
    # Mirror of pm_confidence_score.score (top-level); validator enforces parity
    pm_confidence_score: Optional[float] = None


class ProjectUnderstanding(BaseModel):
    primary_goal: Optional[Any] = None
    beneficiary: Optional[Any] = None
    trigger: Optional[Any] = None
    success_definition: Optional[Any] = None
    supporting_quotes: Optional[Any] = None


class Assumption(BaseModel):
    # All flexible - LLM may output variations
    id: Optional[Any] = None
    what: Optional[Any] = None
    why: Optional[Any] = None
    pmi_basis: Optional[Any] = None
    risk_if_wrong: Optional[Any] = None
    consequence: Optional[Any] = None
    source: Optional[Any] = None


class CriticalPathSummary(BaseModel):
    # Flexible for LLM variations
    sequence: Optional[Any] = None
    total_duration_days: Optional[Any] = None
    zero_slack_tasks: Optional[Any] = None
    highest_slack_tasks: Optional[Any] = None
    staffing_implication: Optional[Any] = None


class Task(BaseModel):
    # All flexible for LLM variations
    id: Optional[Any] = None
    name: Optional[Any] = None
    phase: Optional[Any] = None
    effort_hours: Optional[Any] = None
    owner_role: Optional[Any] = None
    dependencies: Optional[Any] = None
    risk_flag: Optional[Any] = None
    critical_path: Optional[Any] = None
    slack_days: Optional[Any] = None
    definition_of_done: Optional[Any] = None


class Phase(BaseModel):
    # Flexible
    phase_number: Optional[Any] = None
    name: Optional[Any] = None
    duration_weeks: Optional[Any] = None
    percentage_of_total: Optional[Any] = None
    milestones: Optional[Any] = None
    tasks: Optional[Any] = None


class ProjectPlan(BaseModel):
    # All flexible
    total_duration_weeks: Optional[Any] = None
    buffer_applied_percent: Optional[Any] = None
    critical_path_summary: Optional[Any] = None
    phases: Optional[Any] = None


class Risk(BaseModel):
    # All flexible
    id: Optional[Any] = None
    category: Optional[Any] = None
    description: Optional[Any] = None
    probability: Optional[Any] = None
    impact: Optional[Any] = None
    score: Optional[Any] = None
    trigger: Optional[Any] = None
    mitigation: Optional[Any] = None
    contingency: Optional[Any] = None


class StaffingPlanItem(BaseModel):
    # All flexible
    role: Optional[Any] = None
    phase_involvement: Optional[Any] = None
    total_hours: Optional[Any] = None
    allocation_percent: Optional[Any] = None
    skills_required: Optional[Any] = None
    critical_path: Optional[Any] = None
    notes: Optional[Any] = None


class OpenQuestion(BaseModel):
    # All flexible
    priority: Optional[Any] = None
    question: Optional[Any] = None
    urgency: Optional[Any] = None
    impact_if_unanswered: Optional[Any] = None


class Deduction(BaseModel):
    # All flexible
    amount: Optional[Any] = None
    reason: Optional[Any] = None


class ViabilityStatus(str, Enum):
    VIABLE = "VIABLE"
    AT_RISK = "AT_RISK"
    NOT_VIABLE = "NOT_VIABLE"
    CANNOT_ASSESS = "CANNOT_ASSESS"


class GapType(str, Enum):
    BUDGET = "BUDGET"
    SCHEDULE = "SCHEDULE"
    BOTH = "BOTH"
    NA = "N/A"


class ScopingOption(BaseModel):
    option_id: str
    description: str
    impact: str
    tradeoffs: str


class ProjectViability(BaseModel):
    """Project viability assessment - only included when constraints are provided."""
    # Make all optional to handle LLM variations
    viability_status: Optional[Any] = None
    gap_type: Optional[Any] = None
    gap_amount: Optional[Any] = None
    scoping_options: Optional[Any] = None


class PMConfidenceScore(BaseModel):
    # Flexible for LLM variations
    score: Optional[Any] = None
    deductions: Optional[Any] = None
    interpretation: Optional[Any] = None


# --- Main Output Model ---

class PMReport(BaseModel):
    """Complete PM Digital Twin report output model."""
    # Make fields more flexible - use Optional with defaults
    report_metadata: Optional[ReportMetadata] = None
    project_understanding: Optional[ProjectUnderstanding] = None
    assumption_log: Optional[List[Any]] = Field(default_factory=list)
    project_plan: Optional[ProjectPlan] = None
    risk_register: Optional[List[Any]] = Field(default_factory=list)
    staffing_plan: Optional[List[Any]] = Field(default_factory=list)
    open_questions: Optional[List[Any]] = Field(default_factory=list)
    pm_confidence_score: Optional[PMConfidenceScore] = None
    
    # Project viability - only included when constraints are provided
    project_viability: Optional[ProjectViability] = None
    
    # Handle parse errors
    parse_error: Optional[bool] = None
    raw_output: Optional[str] = None
