"""
Partial output schemas for P3 multi-agent pipeline.

Each class represents the intermediate artifact produced by one agent and
consumed by downstream agents. These are NOT the final PMReport — they are
the typed data contracts passed through the orchestrator pipeline.

Reuses nested models from output_schema.py where shapes are identical.
All artifact fields are Optional[Any] (same pattern as PMReport) to tolerate
LLM output variation. The Synthesis agent applies cross-section consistency
rules before assembling the final report.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Constraints (new intermediate concept, not in PMReport)
# Extracted by Intake so downstream agents don't re-read the raw brief.
# ---------------------------------------------------------------------------

class HardConstraints(BaseModel):
    deadline: Optional[str] = None           # e.g. "2025-12-31" or "6 months"
    budget: Optional[str] = None             # e.g. "$50,000" or "£200k"
    team_size: Optional[int] = None
    team_composition: Optional[str] = None   # e.g. "2 devs, 1 designer"
    technology_stack: Optional[str] = None
    compliance: Optional[str] = None         # e.g. "HIPAA", "GDPR"


class SoftConstraints(BaseModel):
    preferred_timeline: Optional[str] = None
    preferred_tools: Optional[str] = None
    nice_to_have: List[str] = Field(default_factory=list)


class NfrConstraints(BaseModel):
    security: Optional[str] = None
    data_retention: Optional[str] = None
    performance: Optional[str] = None
    availability: Optional[str] = None


class ConstraintsBlock(BaseModel):
    hard: HardConstraints = Field(default_factory=HardConstraints)
    soft: SoftConstraints = Field(default_factory=SoftConstraints)
    nfr: NfrConstraints = Field(default_factory=NfrConstraints)


# ---------------------------------------------------------------------------
# Use Case Agent artifact
# ---------------------------------------------------------------------------

class ActorItem(BaseModel):
    id: str                                  # e.g. "A1"
    name: str
    type: str = "primary"                    # "primary" | "secondary" | "external"


class UseCaseItem(BaseModel):
    id: str                                  # e.g. "UC1"
    name: str
    actors: List[str] = Field(default_factory=list)   # actor ids
    complexity: str = "medium"               # "simple" | "medium" | "complex"
    description: Optional[str] = None


class RelationshipItem(BaseModel):
    type: str                                # "includes" | "extends" | "association"
    from_id: str                             # actor id or UC id
    to_id: str                               # UC id


class UseCaseModel(BaseModel):
    """Output of Use Case Agent. Consumed by all downstream agents."""
    system_boundary: Optional[str] = None
    actors: List[ActorItem] = Field(default_factory=list)
    use_cases: List[UseCaseItem] = Field(default_factory=list)
    relationships: List[RelationshipItem] = Field(default_factory=list)
    diagram_xml: Optional[str] = None        # draw.io XML, populated by drawio_generator.py
    diagram_png_bytes: Optional[bytes] = None  # best-effort PNG from Kroki
    input_quality_signal: Optional[str] = None  # "HIGH" | "MEDIUM" | "LOW"
    anti_patterns_detected: List[str] = Field(default_factory=list)
    # Raw token usage for this agent call
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


# ---------------------------------------------------------------------------
# Intake Agent artifact
# ---------------------------------------------------------------------------

class StructuredBrief(BaseModel):
    """
    Output of Intake Agent (Steps 1–4).
    Locks project_understanding and assumption_log for refinement runs —
    downstream agents receive this artifact unchanged on targeted refines.
    """
    project_understanding: Optional[Any] = None   # ProjectUnderstanding shape
    assumption_log: List[Any] = Field(default_factory=list)
    report_metadata: Optional[Any] = None          # ReportMetadata shape
    constraints: ConstraintsBlock = Field(default_factory=ConstraintsBlock)
    open_questions_pre_planning: List[Any] = Field(default_factory=list)
    # Raw token usage
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


# ---------------------------------------------------------------------------
# Planning Agent artifact
# ---------------------------------------------------------------------------

class ProjectPlanArtifact(BaseModel):
    """
    Output of Planning Agent (Steps 5–6).
    use_case_task_mapping enables Synthesis to verify every UC has tasks.
    """
    project_plan: Optional[Any] = None             # ProjectPlan shape
    use_case_task_mapping: Dict[str, List[str]] = Field(default_factory=dict)
    # e.g. {"UC1": ["T1", "T3"], "UC2": ["T4", "T5"]}
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


# ---------------------------------------------------------------------------
# Risk Agent artifact
# ---------------------------------------------------------------------------

class RiskRegisterArtifact(BaseModel):
    """
    Output of Risk Agent (Step 7).
    critical_path_risk_flags: task IDs that Risk agent flags as high-risk.
    Staffing uses this to set critical_path=true on the owning role.
    """
    risk_register: List[Any] = Field(default_factory=list)
    risk_use_case_mapping: Dict[str, List[str]] = Field(default_factory=dict)
    # e.g. {"R1": ["UC2"], "R3": ["UC1", "UC3"]}
    critical_path_risk_flags: List[str] = Field(default_factory=list)
    # task IDs whose owner role must be marked critical_path=true in staffing
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


# ---------------------------------------------------------------------------
# Staffing Agent artifact
# ---------------------------------------------------------------------------

class StaffingPlanArtifact(BaseModel):
    """
    Output of Staffing Agent (Step 8 + viability).
    actor_role_mapping enables Synthesis to verify actor ↔ role coverage.
    pm_confidence_score here is the agent's self-reported score — Synthesis
    recomputes and replaces it with a verified value.
    """
    staffing_plan: List[Any] = Field(default_factory=list)
    open_questions: List[Any] = Field(default_factory=list)
    pm_confidence_score: Optional[Any] = None      # PMConfidenceScore shape
    project_viability: Optional[Any] = None        # ProjectViability shape
    actor_role_mapping: Dict[str, List[str]] = Field(default_factory=dict)
    # e.g. {"A1": ["Frontend Developer", "QA Engineer"], "A2": ["Backend Developer"]}
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


# ---------------------------------------------------------------------------
# Synthesis Agent artifact
# ---------------------------------------------------------------------------

class ConsistencyIssue(BaseModel):
    rule: str           # which consistency rule fired, e.g. "actor_role_coverage"
    detail: str         # human-readable description of the gap
    auto_corrected: bool = False


class StaffingCorrection(BaseModel):
    """A single staffing row to add or update (from Synthesis Rules 1–2)."""
    action: str                             # "add_role" | "set_critical_path"
    role: str
    phase_involvement: List[int] = Field(default_factory=list)
    total_hours: Optional[float] = None
    allocation_percent: Optional[float] = None
    skills_required: List[str] = Field(default_factory=list)
    critical_path: Optional[bool] = None
    notes: Optional[str] = None


class SynthesisResult(BaseModel):
    """
    Delta-only output of Synthesis Agent.
    The orchestrator merges these corrections with the upstream artifacts
    to assemble the final PMReport — Synthesis does NOT re-emit input data.
    """
    consistency_issues: List[ConsistencyIssue] = Field(default_factory=list)
    corrections_applied: List[str] = Field(default_factory=list)
    staffing_corrections: List[StaffingCorrection] = Field(default_factory=list)
    added_open_questions: List[Any] = Field(default_factory=list)
    pm_confidence_score: Optional[Any] = None   # recomputed PMConfidenceScore shape
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


# ---------------------------------------------------------------------------
# Cross-pipeline tracking
# ---------------------------------------------------------------------------

class TokenTally(BaseModel):
    """Accumulates token usage across all agent calls in one pipeline run."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    def add(self, result: dict) -> None:
        """Add token counts from a BaseAgent.run() / run_async() result dict."""
        self.input_tokens += result.get("input_tokens", 0)
        self.output_tokens += result.get("output_tokens", 0)
        self.cache_read_tokens += result.get("cache_read_tokens", 0)
        self.cache_creation_tokens += result.get("cache_creation_tokens", 0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class PipelineResult(BaseModel):
    """
    Return type of PipelineOrchestrator.run() and .refine().

    Two modes:
      - Success:  final_report is populated, paused_at is None
      - Gate fire: paused_at names the stage, partial_artifacts holds what
                   completed so far, final_report is None
    """
    # Success path — orchestrator assembles final_report from all agent artifacts
    final_report: Optional[Dict[str, Any]] = None
    synthesis_corrections: List[str] = Field(default_factory=list)
    # synthesis_corrections mirrors SynthesisResult.corrections_applied for gate context

    # Gate-pause path
    paused_at: Optional[str] = None          # stage name, e.g. "intake"
    gate_signal: Optional[str] = None        # reason string surfaced to the API

    # Partial artifacts available regardless of outcome (for checkpoint resume)
    partial_artifacts: Dict[str, Any] = Field(default_factory=dict)

    # Token usage for the whole run
    token_tally: TokenTally = Field(default_factory=TokenTally)

    @property
    def succeeded(self) -> bool:
        return self.final_report is not None and self.paused_at is None
