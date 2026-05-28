import { useCallback, useEffect, useRef, useState } from "react"

import { planrApiFetch } from "@/lib/planr-user"
import { computeReportDiff } from "@/lib/report-diff"
import { extractPrdText } from "@/lib/prd-upload"
import {
  buildStashFromLiveState,
  getSessionStash,
  listStashedChatsForSidebar,
  mergeStashWithServerEntry,
  removeSessionStash,
  stashSessionState,
} from "@/lib/session-stash"
import {
  buildThreadFromReportEntry,
  splitComposedSessionBrief,
  type PersistedReportEntry,
} from "@/lib/session-hydration"
import type {
  ChatHistoryEntry,
  GateDTO,
  PlanVersionSnapshot,
  ReportRecord,
  SessionSummary,
  ThreadMessage,
  WorkflowPhase,
} from "@/types/plan"

/** Combined brief + PRD text must reach this length before send is enabled. */
const MIN_BRIEF_CHARS = 20
const MIN_BRIEF_WORDS = 4

function tid(): string {
  return crypto.randomUUID()
}

async function readError(res: Response): Promise<string> {
  try {
    const j = (await res.json()) as { detail?: unknown }
    if (typeof j.detail === "string") return j.detail
    if (Array.isArray(j.detail)) return j.detail.map((e: unknown) => {
      if (typeof e === "object" && e !== null && "msg" in e) return (e as { msg: string }).msg
      return String(e)
    }).join("; ")
    if (typeof j.detail === "object" && j.detail !== null) {
      const d = j.detail as Record<string, unknown>
      if (typeof d.message === "string") return d.message
      return JSON.stringify(d)
    }
    return res.statusText || `HTTP ${res.status}`
  } catch {
    return res.statusText || `HTTP ${res.status}`
  }
}

export function useReportWorkflow() {
  const [phase, setPhase] = useState<WorkflowPhase>("IDLE")
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [reportId, setReportId] = useState<string | null>(null)
  const [report, setReport] = useState<ReportRecord | null>(null)
  const [gate, setGate] = useState<GateDTO | null>(null)
  const [brief, setBrief] = useState("")
  const [refineText, setRefineText] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [lastDiff, setLastDiff] = useState<ReturnType<
    typeof computeReportDiff
  > | null>(null)
  const [planVersion, setPlanVersion] = useState(0)
  const [messages, setMessages] = useState<ThreadMessage[]>([])
  const [prdText, setPrdText] = useState("")
  const [prdFileLabel, setPrdFileLabel] = useState<string | null>(null)
  const [prdBusy, setPrdBusy] = useState(false)
  const [agentFailed, setAgentFailed] = useState(false)
  const [sessionSummaries, setSessionSummaries] = useState<SessionSummary[]>(
    []
  )
  const [sessionSwitching, setSessionSwitching] = useState(false)
  const [planSnapshots, setPlanSnapshots] = useState<PlanVersionSnapshot[]>([])
  /** Sidebar rows for plans stashed in sessionStorage (drafts + switch-away state). */
  const [stashedChats, setStashedChats] = useState<ChatHistoryEntry[]>([])
  /** After Start over / New plan, next Generate must bypass agent disk cache (same brief would replay). */
  const skipAgentCacheOnceRef = useRef(false)
  /** Server `report_revision` for optimistic locking on refine / gate decision (409 if stale). */
  const reportRevisionRef = useRef(1)

  const refreshSessionList = useCallback(async () => {
    try {
      const res = await planrApiFetch("/sessions")
      if (!res.ok) return
      const rows = (await res.json()) as SessionSummary[]
      setSessionSummaries(Array.isArray(rows) ? rows : [])
    } catch {
      /* list is optional if API unreachable */
    }
  }, [])

  const refreshStashedSidebar = useCallback((apiRows: SessionSummary[]) => {
    setStashedChats(
      listStashedChatsForSidebar(new Set(apiRows.map((s) => s.session_id)))
    )
  }, [])

  const ensureSession = useCallback(async (): Promise<string> => {
    if (sessionId) return sessionId
    const res = await planrApiFetch("/sessions", { method: "POST" })
    if (!res.ok) throw new Error(await readError(res))
    const j = (await res.json()) as { session_id: string }
    setSessionId(j.session_id)
    return j.session_id
  }, [sessionId])

  const clearPrd = useCallback(() => {
    setPrdText("")
    setPrdFileLabel(null)
  }, [])

  const loadPrdFile = useCallback(async (file: File | null) => {
    if (!file) return
    setPrdBusy(true)
    setError(null)
    try {
      const text = await extractPrdText(file)
      const t = text.trim()
      if (!t) {
        setError("No text extracted from PRD. Try another file.")
        return
      }
      setPrdText(text)
      setPrdFileLabel(file.name)
    } catch (e) {
      setError(e instanceof Error ? e.message : "PRD upload failed")
    } finally {
      setPrdBusy(false)
    }
  }, [])

  const generate = useCallback(async () => {
    const b = brief.trim()
    const p = prdText.trim()
    const effective = `${b}\n${p}`.trim()
    if (effective.length < MIN_BRIEF_CHARS) return
    setError(null)
    setLastDiff(null)
    setPhase("GENERATING")
    const bypassCache = skipAgentCacheOnceRef.current
    if (bypassCache) skipAgentCacheOnceRef.current = false
    const useCache = !bypassCache
    const userMsg: ThreadMessage = {
      id: tid(),
      role: "user",
      variant: "brief",
      content: b || "(PRD only, see attachment)",
      ...(prdFileLabel && p
        ? {
            prdAttachment: {
              filename: prdFileLabel,
              excerptChars: p.length,
            },
          }
        : {}),
    }
    setMessages((m) => [...m, userMsg])
    try {
      const sid = await ensureSession()
      const res = await planrApiFetch("/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sid,
          brief: b,
          prd_text: p || null,
          use_cache: useCache,
        }),
      })
      if (!res.ok) {
        const msg = await readError(res)
        if (res.status === 502) setAgentFailed(true)
        throw new Error(msg)
      }
      setAgentFailed(false)
      const j = (await res.json()) as {
        report_id: string
        report_revision?: number
        report: ReportRecord
        gate: GateDTO
      }
      setPlanSnapshots([])
      setReportId(j.report_id)
      reportRevisionRef.current = typeof j.report_revision === "number" ? j.report_revision : 1
      setReport(j.report)
      setGate(j.gate)
      setPlanVersion(1)
      setMessages((m) => [
        ...m,
        {
          id: tid(),
          role: "assistant",
          variant: "plan_ready",
          version: 1,
          gateFired: j.gate.fired,
        },
      ])
      setPhase("REVIEW")
      void refreshSessionList()
    } catch (e) {
      if (bypassCache) skipAgentCacheOnceRef.current = true
      // Always bypass cache on next attempt after agent failure so the
      // same brief doesn't replay a cached bad output.
      skipAgentCacheOnceRef.current = true
      setError(e instanceof Error ? e.message : "Generate failed")
      setPhase("IDLE")
    }
  }, [brief, ensureSession, prdFileLabel, prdText, refreshSessionList])

  const refine = useCallback(async () => {
    const feedback = refineText.trim()
    if (!reportId || !sessionId || feedback.length < 1) return
    setError(null)
    const priorReport = report
    const priorGate = gate
    setMessages((m) => [
      ...m,
      { id: tid(), role: "user", variant: "refine", content: feedback },
    ])
    setPhase("REFINING")
    try {
      const res = await planrApiFetch(`/reports/${reportId}/refine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          feedback,
          update_brief: false,
          expected_revision: reportRevisionRef.current,
        }),
      })
      if (!res.ok) throw new Error(await readError(res))
      const j = (await res.json()) as {
        report_revision?: number
        report: ReportRecord
        gate: GateDTO
      }
      if (typeof j.report_revision === "number")
        reportRevisionRef.current = j.report_revision
      const nextVersion = planVersion + 1
      if (priorReport != null && priorGate != null) {
        setPlanSnapshots((s) => [
          ...s,
          { version: planVersion, report: priorReport, gate: priorGate },
        ])
      }
      setReport(j.report)
      setGate(j.gate)
      setRefineText("")
      setPlanVersion(nextVersion)
      let diffBlock: ReturnType<typeof computeReportDiff> = null
      if (priorReport) {
        diffBlock = computeReportDiff(
          priorReport,
          j.report,
          priorGate,
          j.gate,
          nextVersion
        )
        setLastDiff(diffBlock)
      }
      if (diffBlock) {
        setMessages((m) => [
          ...m,
          {
            id: tid(),
            role: "assistant",
            variant: "refine_summary",
            title: diffBlock.title,
            lines: diffBlock.lines,
          },
        ])
      }
      setPhase("REVIEW")
      void refreshSessionList()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Refine failed")
      setPhase("REVIEW")
    }
  }, [gate, planVersion, refineText, report, reportId, sessionId, refreshSessionList])

  /** Logs approval on the server and moves to APPROVED (with or without a fired gate). */
  const approve = useCallback(async () => {
    if (!reportId || !sessionId) return
    setError(null)
    try {
      const res = await planrApiFetch(`/gates/${reportId}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          decision: "approve",
          expected_revision: reportRevisionRef.current,
        }),
      })
      if (!res.ok) throw new Error(await readError(res))
      const j = (await res.json()) as { report_revision?: number; gate: GateDTO }
      if (typeof j.report_revision === "number")
        reportRevisionRef.current = j.report_revision
      setGate(j.gate)
      setPhase("APPROVED")
      void refreshSessionList()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed")
    }
  }, [reportId, sessionId, refreshSessionList])

  /**
   * New API session while keeping the same brief + PRD so the PM can run Generate again.
   */
  const startNewPlan = useCallback(async () => {
    const dropId = sessionId
    if (dropId) removeSessionStash(dropId)
    skipAgentCacheOnceRef.current = true
    setError(null)
    try {
      setRefineText("")
      reportRevisionRef.current = 1
      setReport(null)
      setGate(null)
      setLastDiff(null)
      setPlanSnapshots([])
      setReportId(null)
      setPlanVersion(0)
      setSessionId(null)
      setMessages([])
      setBrief("")
      setPrdText("")
      setPrdFileLabel(null)
      setPhase("IDLE")
      const res = await planrApiFetch("/sessions", { method: "POST" })
      if (!res.ok) throw new Error(await readError(res))
      const j = (await res.json()) as { session_id: string }
      setSessionId(j.session_id)
      void refreshSessionList()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start new plan")
    }
  }, [refreshSessionList, sessionId])

  /**
   * Remove the current session from the server (plan history) and start a new empty session.
   * Safe if the session was never persisted (server returns 404).
   */
  const deleteCurrentSession = useCallback(async () => {
    if (!sessionId) return
    removeSessionStash(sessionId)
    setError(null)
    try {
      const res = await planrApiFetch(`/sessions/${sessionId}`, {
        method: "DELETE",
      })
      if (!res.ok && res.status !== 404) {
        throw new Error(await readError(res))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete")
      return
    }
    await startNewPlan()
  }, [sessionId, startNewPlan])

  useEffect(() => {
    refreshStashedSidebar(sessionSummaries)
  }, [sessionSummaries, refreshStashedSidebar])

  /** Load a persisted session from disk (sidebar). Uses the latest report in that session. */
  const switchSession = useCallback(
    async (targetSessionId: string) => {
      if (!targetSessionId) return
      if (targetSessionId === sessionId) return
      if (phase === "GENERATING" || phase === "REFINING") {
        setError("Wait for the current step to finish before switching plans.")
        return
      }
      setError(null)
      if (sessionId && sessionId !== targetSessionId) {
        const hasContent =
          brief.trim().length > 0 || prdText.trim().length > 0 || report !== null
        if (hasContent) {
          try {
            stashSessionState(
              buildStashFromLiveState({
                sessionId,
                brief,
                prdText,
                prdFileLabel,
                phase,
                report,
                gate,
                reportId,
                planVersion,
                planSnapshots,
                messages,
                refineText,
                reportRevision: reportRevisionRef.current,
                agentFailed,
                lastError: error,
              })
            )
          } catch {
            /* quota */
          }
        }
        refreshStashedSidebar(sessionSummaries)
      }
      setSessionSwitching(true)
      setLastDiff(null)
      setRefineText("")
      const applyStash = (s: {
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
      }) => {
        setSessionId(s.sessionId)
        setBrief(s.brief)
        setPrdText(s.prdText)
        setPrdFileLabel(s.prdFileLabel)
        setReport(s.report)
        setGate(s.gate)
        setReportId(s.reportId)
        setPlanVersion(s.planVersion)
        setPlanSnapshots(s.planSnapshots)
        setMessages(s.messages)
        setRefineText(s.refineText)
        reportRevisionRef.current = s.reportRevision
        setAgentFailed(s.agentFailed)
        setError(s.lastError)
        let ph: WorkflowPhase = s.phase
        if (ph === "GENERATING" || ph === "REFINING") {
          ph = s.report ? "REVIEW" : "IDLE"
        }
        setPhase(ph)
        setLastDiff(null)
      }
      try {
        const res = await planrApiFetch(`/sessions/${targetSessionId}`)
        if (res.status === 404) {
          const stash = getSessionStash(targetSessionId)
          if (stash) {
            applyStash(stash)
            setAgentFailed(false)
            void refreshSessionList()
            return
          }
          throw new Error("Session not found")
        }
        if (!res.ok) throw new Error(await readError(res))
        const state = (await res.json()) as {
          session_id: string
          reports: PersistedReportEntry[]
        }
        setSessionId(state.session_id)
        const reports = Array.isArray(state.reports) ? state.reports : []
        if (reports.length === 0) {
          const stash = getSessionStash(targetSessionId)
          if (stash) {
            applyStash(stash)
            setAgentFailed(false)
            void refreshSessionList()
            return
          }
          setReportId(null)
          reportRevisionRef.current = 1
          setReport(null)
          setGate(null)
          setPlanSnapshots([])
          setMessages([])
          setBrief("")
          setPrdText("")
          setPrdFileLabel(null)
          setPlanVersion(0)
          setPhase("IDLE")
          void refreshSessionList()
          return
        }
        const entry = reports[reports.length - 1] as PersistedReportEntry
        const split = splitComposedSessionBrief(entry.brief ?? "")
        setBrief(split.brief)
        setPrdText(split.prdText)
        setPrdFileLabel(split.prdText ? "From session" : null)
        setReportId(entry.report_id)
        const serverRev =
          typeof entry.report_revision === "number" ? entry.report_revision : 1
        reportRevisionRef.current = serverRev
        setReport(entry.report as ReportRecord)
        setGate(entry.gate as GateDTO)
        const refinements = entry.refinements ?? []
        setPlanVersion(1 + refinements.length)
        const stash = getSessionStash(targetSessionId)
        if (mergeStashWithServerEntry(stash, entry).useStash && stash) {
          setPlanSnapshots(stash.planSnapshots)
          setMessages(stash.messages)
          setRefineText(stash.refineText)
          const approved = entry.gate?.decision === "approve"
          if (approved) {
            setPhase("APPROVED")
          } else {
            let ph: WorkflowPhase = stash.phase
            if (ph === "GENERATING" || ph === "REFINING" || ph === "APPROVED")
              ph = "REVIEW"
            setPhase(ph)
          }
          removeSessionStash(targetSessionId)
        } else {
          if (stash) removeSessionStash(targetSessionId)
          setPlanSnapshots([])
          setMessages(
            buildThreadFromReportEntry(
              entry,
              split.brief,
              split.prdText,
              split.prdText ? "From session" : null
            )
          )
          const approved = entry.gate?.decision === "approve"
          setPhase(approved ? "APPROVED" : "REVIEW")
        }
        void refreshSessionList()
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not open session")
      } finally {
        setSessionSwitching(false)
        refreshStashedSidebar(sessionSummaries)
      }
    },
    [
      sessionId,
      sessionSummaries,
      phase,
      brief,
      prdText,
      prdFileLabel,
      report,
      gate,
      reportId,
      planVersion,
      planSnapshots,
      messages,
      refineText,
      error,
      agentFailed,
      refreshSessionList,
      refreshStashedSidebar,
    ]
  )

  const effectiveInputLength = `${brief.trim()}\n${prdText.trim()}`.trim().length
  const hasPrd = prdText.trim().length > 0
  const briefWordCount = brief.trim().split(/\s+/).filter(Boolean).length
  const briefWordsOk = hasPrd || briefWordCount >= MIN_BRIEF_WORDS
  const canSubmit = effectiveInputLength >= MIN_BRIEF_CHARS && briefWordsOk
  const canRefine = refineText.trim().length >= 1

  const bootstrapSession = useCallback(async () => {
    try {
      await ensureSession()
      await refreshSessionList()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create session")
    }
  }, [ensureSession, refreshSessionList])

  return {
    phase,
    sessionId,
    reportId,
    report,
    gate,
    brief,
    setBrief,
    refineText,
    setRefineText,
    error,
    setError,
    agentFailed,
    clearAgentFailed: () => setAgentFailed(false),
    lastDiff,
    planVersion,
    generate,
    refine,
    approve,
    startNewPlan,
    deleteCurrentSession,
    canSubmit,
    prdText,
    prdFileLabel,
    prdBusy,
    loadPrdFile,
    clearPrd,
    canRefine,
    minBriefChars: MIN_BRIEF_CHARS,
    effectiveInputLength,
    bootstrapSession,
    messages,
    sessionSummaries,
    refreshSessionList,
    switchSession,
    sessionSwitching,
    planSnapshots,
    stashedChats,
  }
}
