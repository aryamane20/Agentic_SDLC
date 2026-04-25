import {
  PLAN_REPORT_ROOT,
  PROJECT_PLAN_FIELDS,
} from "@/lib/plan-display-profile"
import type { GateDTO, ReportRecord } from "@/types/plan"

function weeks(r: ReportRecord | null): string | number | undefined {
  const plan = r?.[PLAN_REPORT_ROOT.projectPlan] as
    | Record<string, unknown>
    | undefined
  return plan?.[PROJECT_PLAN_FIELDS.totalDurationWeeks] as
    | string
    | number
    | undefined
}

function confidence(r: ReportRecord | null): string | number | undefined {
  const pm = r?.[PLAN_REPORT_ROOT.pmConfidenceScore] as
    | Record<string, unknown>
    | undefined
  return pm?.score as string | number | undefined
}

function confidenceInterpretation(r: ReportRecord | null): string | undefined {
  const pm = r?.[PLAN_REPORT_ROOT.pmConfidenceScore] as
    | Record<string, unknown>
    | undefined
  const i = pm?.interpretation
  return i != null ? String(i) : undefined
}

function riskCount(r: ReportRecord | null): number {
  const reg = r?.[PLAN_REPORT_ROOT.riskRegister]
  return Array.isArray(reg) ? reg.length : 0
}

export type RefineDiffBlock = {
  title: string
  lines: string[]
}

/**
 * Client-only summary after refine: diff duration, confidence, risks, gate.
 * No LLM — four structured reads + gate reasons.
 */
export function computeReportDiff(
  prior: ReportRecord | null,
  next: ReportRecord,
  priorGate: GateDTO | null,
  nextGate: GateDTO,
  version: number
): RefineDiffBlock | null {
  if (!prior) return null

  const lines: string[] = []

  const w0 = weeks(prior)
  const w1 = weeks(next)
  if (w0 !== w1) {
    lines.push(`Timeline:    ${w0 ?? "-"} weeks -> ${w1 ?? "-"} weeks`)
  }

  const c0 = confidence(prior)
  const c1 = confidence(next)
  if (c0 !== c1) {
    const interp = confidenceInterpretation(next)
    const extra = interp
      ? ` (${interp.length > 90 ? `${interp.slice(0, 87)}…` : interp})`
      : ""
    lines.push(`Confidence:  ${c0 ?? "-"} -> ${c1 ?? "-"}${extra}`)
  }

  const r0 = riskCount(prior)
  const r1 = riskCount(next)
  if (r0 !== r1) {
    lines.push(`Risks:       ${r0} → ${r1} register items`)
  }

  if (nextGate.fired) {
    const reasons =
      nextGate.reasons?.length > 0
        ? nextGate.reasons.join("; ")
        : "See approval gate details"
    lines.push(`Gate:        ⚠ Fired: ${reasons}`)
  } else if (priorGate?.fired && !nextGate.fired) {
    lines.push(`Gate:        Cleared (no blocking issues)`)
  }

  if (lines.length === 0) {
    lines.push(`Plan structure updated. Review full plan below.`)
  }

  return {
    title: `Plan updated: v${version}`,
    lines,
  }
}
