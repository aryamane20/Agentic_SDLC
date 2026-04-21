import type { GateDTO, ReportRecord, ThreadMessage } from "@/types/plan"

const PRD_MARKER = "--- ATTACHED PRD ---"

export type PersistedReportEntry = {
  report_id: string
  brief: string
  report: ReportRecord
  gate: GateDTO
  report_revision?: number
  refinements?: Array<{ feedback: string }>
}

export function splitComposedSessionBrief(composed: string): {
  brief: string
  prdText: string
} {
  const c = (composed || "").trim()
  const i = c.indexOf(PRD_MARKER)
  if (i === -1) return { brief: c, prdText: "" }
  return {
    brief: c.slice(0, i).trim(),
    prdText: c.slice(i + PRD_MARKER.length).trim(),
  }
}

function rid(): string {
  return crypto.randomUUID()
}

/** Rebuild sidebar thread from the latest report entry on the server. */
export function buildThreadFromReportEntry(
  entry: PersistedReportEntry,
  displayBrief: string,
  prdText: string,
  prdLabel: string | null
): ThreadMessage[] {
  const msgs: ThreadMessage[] = []
  msgs.push({
    id: rid(),
    role: "user",
    variant: "brief",
    content: displayBrief || (prdText ? "(PRD only — see attachment)" : ""),
    ...(prdText && prdLabel
      ? { prdAttachment: { filename: prdLabel, excerptChars: prdText.length } }
      : prdText
        ? {
            prdAttachment: {
              filename: "From session",
              excerptChars: prdText.length,
            },
          }
        : {}),
  })
  msgs.push({
    id: rid(),
    role: "assistant",
    variant: "plan_ready",
    version: 1,
    gateFired: Boolean(entry.gate?.fired),
  })
  const refs = entry.refinements ?? []
  let v = 2
  for (const r of refs) {
    msgs.push({
      id: rid(),
      role: "user",
      variant: "refine",
      content: r.feedback,
    })
    msgs.push({
      id: rid(),
      role: "assistant",
      variant: "refine_summary",
      title: `Plan updated — v${v}`,
      lines: ["Refinement applied."],
    })
    v++
  }
  return msgs
}
