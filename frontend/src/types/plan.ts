/** One saved plan row from GET /sessions (latest brief preview; ≥1 generated report). */
export type SessionSummary = {
  session_id: string
  report_count: number
  updated_at: number
  preview: string
}

/** Sidebar row: saved plans plus optional local draft before first generate. */
export type ChatHistoryEntry = SessionSummary & {
  isLocalDraft?: boolean
}

/** Mirrors backend GateState JSON. */
export type GateDTO = {
  fired: boolean
  reasons: string[]
  decision?: "approve" | "reject" | null
}

export type ReportRecord = Record<string, unknown>

export type WorkflowPhase =
  | "IDLE"
  | "GENERATING"
  | "REVIEW"
  | "REFINING"
  | "APPROVED"

/** Transcript bubbles for Studio glass animated thread. */
export type ThreadMessage =
  | {
      id: string
      role: "user"
      variant: "brief"
      content: string
      prdAttachment?: { filename: string; excerptChars: number }
    }
  | { id: string; role: "user"; variant: "refine"; content: string }
  | {
      id: string
      role: "assistant"
      variant: "plan_ready"
      version: number
      gateFired: boolean
    }
  | {
      id: string
      role: "assistant"
      variant: "refine_summary"
      title: string
      lines: string[]
    }
