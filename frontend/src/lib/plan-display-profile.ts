/**
 * Single place to map PM report JSON → in-app sections/labels/columns.
 * Keep keys aligned with `schemas/output_schema.py` (`PMReport` and nested models).
 * When the Pydantic model renames a field, update this file (and sample JSON if needed).
 */

import type { ReportRecord } from "@/types/plan"

/** Top-level keys on the report object — mirrors `PMReport` in output_schema.py */
export const PLAN_REPORT_ROOT = {
  reportMetadata: "report_metadata",
  projectUnderstanding: "project_understanding",
  assumptionLog: "assumption_log",
  projectPlan: "project_plan",
  riskRegister: "risk_register",
  staffingPlan: "staffing_plan",
  openQuestions: "open_questions",
  pmConfidenceScore: "pm_confidence_score",
  projectViability: "project_viability",
  parseError: "parse_error",
  rawOutput: "raw_output",
} as const

export const PLAN_SECTIONS = {
  metadata: { id: "metadata", title: "Metadata" },
  projectContext: { id: "context", title: "Project context" },
  assumptions: { id: "assumptions", title: "Assumptions" },
  plan: { id: "plan", title: "Plan & phases" },
  risks: { id: "risks", title: "Risks" },
  staffing: { id: "staffing", title: "Staffing" },
  openQuestions: { id: "questions", title: "Open questions" },
  viability: { id: "viability", title: "Viability" },
} as const

export type PillTone = "neutral" | "blue" | "amber" | "emerald" | "rose"

/** Metadata fields rendered as pills (values from `report_metadata`) */
export const METADATA_PILL_FIELDS: ReadonlyArray<{
  field: string
  prefix: string
  tone?: PillTone
}> = [
  { field: "sdlc_approach", prefix: "SDLC: ", tone: "blue" },
]

export const METADATA_TEXT_FIELDS = {
  generatedAt: "generated_at",
  sdlcRationale: "sdlc_rationale",
} as const

/** Flat `pm_confidence_score` sometimes appears on metadata in legacy samples */
export const METADATA_LEGACY_PM_SCORE_FIELD = "pm_confidence_score" as const

export const PM_CONFIDENCE_PILL = {
  prefix: "PM confidence: ",
  tone: "emerald" as const satisfies PillTone,
}

/** Definition list rows under project_understanding */
export const PROJECT_CONTEXT_FIELDS: ReadonlyArray<{
  field: string
  label: string
}> = [
  { field: "primary_goal", label: "Goal" },
  { field: "beneficiary", label: "Beneficiary" },
  { field: "trigger", label: "Trigger" },
  { field: "success_definition", label: "Success" },
]

export const PROJECT_CONTEXT_QUOTES_FIELD = "supporting_quotes" as const

/** Direct fields on `project_plan` — mirrors `ProjectPlan` in output_schema.py */
export const PROJECT_PLAN_FIELDS = {
  totalDurationWeeks: "total_duration_weeks",
  bufferAppliedPercent: "buffer_applied_percent",
  phases: "phases",
} as const

export const PLAN_SUMMARY_PILLS: ReadonlyArray<{
  field: string
  prefix: string
  suffix: string
}> = [
  {
    field: PROJECT_PLAN_FIELDS.totalDurationWeeks,
    prefix: "Duration: ",
    suffix: " wk",
  },
  {
    field: PROJECT_PLAN_FIELDS.bufferAppliedPercent,
    prefix: "Buffer: ",
    suffix: "%",
  },
]

export const PLAN_CRITICAL_PATH_KEY = "critical_path_summary" as const

export const PHASE_FIELDS = {
  phaseNumber: "phase_number",
  name: "name",
  durationWeeks: "duration_weeks",
  percentageOfTotal: "percentage_of_total",
  milestones: "milestones",
  tasks: "tasks",
} as const

export const ASSUMPTION_TABLE = {
  headers: ["ID", "What", "Why / basis", "Risk if wrong"] as const,
} as const

export const TASK_TABLE = {
  headers: ["ID", "Task", "Owner", "Hrs", "Flags"] as const,
  flagCritical: "critical_path",
  flagRisk: "risk_flag",
} as const

export const RISK_TABLE = {
  headers: ["ID", "Category", "Description", "P×I", "Mitigation"] as const,
  fields: {
    id: "id",
    category: "category",
    description: "description",
    probability: "probability",
    impact: "impact",
    score: "score",
    mitigation: "mitigation",
  },
} as const

export const STAFFING_TABLE = {
  headers: [
    "Role",
    "Phases",
    "Hours",
    "Alloc %",
    "Skills",
    "Notes",
  ] as const,
  fields: {
    role: "role",
    phaseInvolvement: "phase_involvement",
    totalHours: "total_hours",
    allocationPercent: "allocation_percent",
    skillsRequired: "skills_required",
    criticalPath: "critical_path",
    notes: "notes",
  },
} as const

export const OPEN_QUESTION_FIELDS = {
  question: "question",
  urgency: "urgency",
  impactIfUnanswered: "impact_if_unanswered",
} as const

export const UI_LABELS = {
  supportingQuotes: "Supporting quotes",
  milestones: "Milestones",
  criticalPathHeading: "Critical path",
  phaseTimelineSuffix: "% of timeline",
  weekSuffix: "wk",
  gateBlocking: "Gate: blocking",
  gateClear: "Gate: clear",
  gateBlockingHint: "Resolve or approve after review",
  parseWarningTitle: "Parse warning",
  emptyAssumptions: "No assumptions listed.",
  emptyPlan: "No project plan block.",
  emptyPhases: "No phases.",
  emptyPhaseTasks: "No tasks in this phase.",
  emptyRisks: "No risks in register.",
  emptyStaffing: "No staffing plan.",
  criticalPathBadge: "critical path",
} as const

export function getMetadataObject(
  report: ReportRecord
): Record<string, unknown> | undefined {
  const m = report[PLAN_REPORT_ROOT.reportMetadata]
  return m && typeof m === "object" && !Array.isArray(m)
    ? (m as Record<string, unknown>)
    : undefined
}

export function getPmConfidence(report: ReportRecord): {
  score: number | string | undefined
  interpretation?: string
} {
  const meta = getMetadataObject(report)
  const metaFlat = meta?.[METADATA_LEGACY_PM_SCORE_FIELD]
  const top = report[PLAN_REPORT_ROOT.pmConfidenceScore]

  // Canonical numeric is pm_confidence_score.score (object); metadata is a mirror only.
  if (top && typeof top === "object" && !Array.isArray(top)) {
    const o = top as Record<string, unknown>
    const raw = o.score ?? o.Score
    const score =
      typeof raw === "number" || typeof raw === "string" ? raw : undefined
    const interpretation =
      o.interpretation != null ? String(o.interpretation) : undefined
    return { score, interpretation }
  }
  if (typeof top === "number" || typeof top === "string") {
    return { score: top }
  }
  if (typeof metaFlat === "number" || typeof metaFlat === "string") {
    return { score: metaFlat }
  }
  return { score: undefined }
}

export function formatAssumptionWhyBasis(o: Record<string, unknown>): string {
  const parts = [o.why, o.pmi_basis].filter(
    (x) => x != null && String(x).trim() !== ""
  )
  return parts.map((x) => String(x)).join(" · ") || "-"
}

export function formatAssumptionRiskIfWrong(o: Record<string, unknown>): string {
  if (o.risk_if_wrong != null) return String(o.risk_if_wrong)
  if (o.consequence != null) return String(o.consequence)
  return "-"
}
