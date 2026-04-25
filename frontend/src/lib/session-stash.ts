/**
 * When switching between sidebar chats, the server only persists sessions
 * after the first successful Generate. Draft briefs and in-memory "Earlier
 * version" planSnapshots also need to survive navigation — we stash them
 * in sessionStorage keyed by session_id.
 */
import type {
  ChatHistoryEntry,
  GateDTO,
  PlanVersionSnapshot,
  ReportRecord,
  ThreadMessage,
  WorkflowPhase,
} from "@/types/plan"
import type { PersistedReportEntry } from "@/lib/session-hydration"

const PREFIX = "planr:bx:"

export type StashedClientStateV1 = {
  v: 1
  sessionId: string
  stashedAt: number
  brief: string
  prdText: string
  prdFileLabel: string | null
  phase: WorkflowPhase
  report: ReportRecord | null
  gate: GateDTO | null
  reportId: string | null
  planVersion: number
  planSnapshots: PlanVersionSnapshot[]
  messages: ThreadMessage[]
  refineText: string
  reportRevision: number
  agentFailed: boolean
  lastError: string | null
}

function key(id: string): string {
  return `${PREFIX}${id}`
}

export function stashSessionState(state: StashedClientStateV1): void {
  try {
    sessionStorage.setItem(key(state.sessionId), JSON.stringify(state))
  } catch {
    /* quota */
  }
}

export function getSessionStash(
  sessionId: string
): StashedClientStateV1 | null {
  try {
    const raw = sessionStorage.getItem(key(sessionId))
    if (!raw) return null
    const p = JSON.parse(raw) as StashedClientStateV1
    if (p.v !== 1 || p.sessionId !== sessionId) return null
    return p
  } catch {
    return null
  }
}

export function removeSessionStash(sessionId: string): void {
  try {
    sessionStorage.removeItem(key(sessionId))
  } catch {
    /* ignore */
  }
}

/**
 * All stashed session ids in storage (any tab), for the sidebar.
 */
export function listStashSessionIds(): string[] {
  if (typeof sessionStorage === "undefined") return []
  const out: string[] = []
  for (let i = 0; i < sessionStorage.length; i += 1) {
    const k = sessionStorage.key(i)
    if (k?.startsWith(PREFIX)) {
      out.push(k.slice(PREFIX.length))
    }
  }
  return out
}

function previewFromStash(s: StashedClientStateV1): string {
  if (s.report) {
    return s.phase === "APPROVED"
      ? (s.brief.trim() || "Approved plan").slice(0, 120)
      : (s.brief.trim() || "Plan in progress").slice(0, 120)
  }
  const t = `${s.brief}\n${s.prdText}`.trim()
  if (t) return t.slice(0, 120)
  return "Draft — not saved to server"
}

/**
 * Build sidebar entries for stashed sessions that are not on the server list yet.
 */
export function listStashedChatsForSidebar(
  alreadyInApi: Set<string>
): ChatHistoryEntry[] {
  const rows: ChatHistoryEntry[] = []
  for (const id of listStashSessionIds()) {
    if (alreadyInApi.has(id)) continue
    const s = getSessionStash(id)
    if (!s) {
      removeSessionStash(id)
      continue
    }
    rows.push({
      session_id: id,
      report_count: s.report ? 1 : 0,
      updated_at: Math.floor(s.stashedAt / 1000),
      preview: previewFromStash(s),
      isLocalDraft: true,
    })
  }
  rows.sort((a, b) => b.updated_at - a.updated_at)
  return rows
}

/**
 * If server and stash agree on report identity+revision, restore rich UI
 * (plan snapshots + full thread) from the stash; otherwise return null to
 * use server-only rebuild.
 */
export function mergeStashWithServerEntry(
  stash: StashedClientStateV1 | null,
  lastEntry: PersistedReportEntry
): { useStash: boolean } {
  if (!stash || !lastEntry) return { useStash: false }
  if (stash.reportId !== lastEntry.report_id) return { useStash: false }
  const serverRev = lastEntry.report_revision ?? 1
  if ((stash.reportRevision || 1) !== serverRev) return { useStash: false }
  return { useStash: true }
}

export function buildStashFromLiveState(
  pack: Omit<StashedClientStateV1, "v" | "stashedAt"> & { sessionId: string }
): StashedClientStateV1 {
  return {
    v: 1,
    stashedAt: Date.now(),
    ...pack,
  }
}
