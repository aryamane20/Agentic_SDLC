import { useCallback, useRef, useState } from "react"

import { planrApiFetch } from "@/lib/planr-user"
import { computeReportDiff } from "@/lib/report-diff"
import { extractPrdText } from "@/lib/prd-upload"
import {
  buildThreadFromReportEntry,
  splitComposedSessionBrief,
  type PersistedReportEntry,
} from "@/lib/session-hydration"
import type {
  GateDTO,
  PlanVersionSnapshot,
  ReportRecord,
  SessionSummary,
  ThreadMessage,
  WorkflowPhase,
} from "@/types/plan"

/** Combined brief + PRD text must reach this length before send is enabled. */
const MIN_BRIEF = 10

function tid(): string {
  return crypto.randomUUID()
}

async function readError(res: Response): Promise<string> {
  try {
    const j = (await res.json()) as { detail?: unknown }
    if (typeof j.detail === "string") return j.detail
    if (Array.isArray(j.detail)) return JSON.stringify(j.detail)
    if (typeof j.detail === "object" && j.detail !== null)
      return JSON.stringify(j.detail)
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
        setError("No text extracted from PRD — try another file.")
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
    if (effective.length < MIN_BRIEF) return
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
      content: b || "(PRD only — see attachment)",
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
    const keepBrief = brief
    const keepPrd = prdText
    const keepLabel = prdFileLabel
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
      setPhase("IDLE")
      const res = await planrApiFetch("/sessions", { method: "POST" })
      if (!res.ok) throw new Error(await readError(res))
      const j = (await res.json()) as { session_id: string }
      setSessionId(j.session_id)
      setBrief(keepBrief)
      setPrdText(keepPrd)
      setPrdFileLabel(keepLabel)
      void refreshSessionList()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start new plan")
    }
  }, [brief, prdFileLabel, prdText, refreshSessionList])

  /** Load a persisted session from disk (sidebar). Uses the latest report in that session. */
  const switchSession = useCallback(
    async (targetSessionId: string) => {
      if (!targetSessionId) return
      if (targetSessionId === sessionId) return
      setError(null)
      setSessionSwitching(true)
      setLastDiff(null)
      setRefineText("")
      try {
        const res = await planrApiFetch(`/sessions/${targetSessionId}`)
        if (!res.ok) throw new Error(await readError(res))
        const state = (await res.json()) as {
          session_id: string
          reports: PersistedReportEntry[]
        }
        setSessionId(state.session_id)
        const reports = Array.isArray(state.reports) ? state.reports : []
        if (reports.length === 0) {
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
        const entry = reports[reports.length - 1]
        setPlanSnapshots([])
        const split = splitComposedSessionBrief(entry.brief ?? "")
        setBrief(split.brief)
        setPrdText(split.prdText)
        setPrdFileLabel(split.prdText ? "From session" : null)
        setReportId(entry.report_id)
        reportRevisionRef.current =
          typeof entry.report_revision === "number" ? entry.report_revision : 1
        setReport(entry.report as ReportRecord)
        setGate(entry.gate as GateDTO)
        const refinements = entry.refinements ?? []
        setPlanVersion(1 + refinements.length)
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
        void refreshSessionList()
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not open session")
      } finally {
        setSessionSwitching(false)
      }
    },
    [refreshSessionList, sessionId]
  )

  const effectiveInputLength = `${brief.trim()}\n${prdText.trim()}`.trim().length
  const canSubmit = effectiveInputLength >= MIN_BRIEF
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
    canSubmit,
    prdText,
    prdFileLabel,
    prdBusy,
    loadPrdFile,
    clearPrd,
    canRefine,
    minBriefLength: MIN_BRIEF,
    effectiveInputLength,
    bootstrapSession,
    messages,
    sessionSummaries,
    refreshSessionList,
    switchSession,
    sessionSwitching,
    planSnapshots,
  }
}
