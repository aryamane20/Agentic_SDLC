import { useEffect, useMemo, useRef, useState } from "react"
import { ChevronDown, Sparkles } from "lucide-react"
import { Link } from "react-router-dom"

import { GateAlert } from "@/components/plan/gate-alert"
import { PlanFloatingComposer } from "@/components/plan/plan-floating-composer"
import { PlanRefineExchange } from "@/components/plan/plan-refine-exchange"
import { PlanReportView } from "@/components/plan/plan-report-view"
import { PlanSidebar } from "@/components/plan/plan-sidebar"
import { PlanWorkingLoader } from "@/components/plan/plan-working-loader"
import { StudioShineBorder } from "@/components/studio/studio-shine-border"
import { Button } from "@/components/ui/button"
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion"
import { useReportWorkflow } from "@/hooks/use-report-workflow"
import { PRD_ACCEPT } from "@/lib/prd-upload"
import type {
  ChatHistoryEntry,
  GateDTO,
  PlanVersionSnapshot,
  ThreadMessage,
} from "@/types/plan"

const BRIEF_PLACEHOLDER = "Describe your initiative, or attach a PRD with +"
const REFINE_PLACEHOLDER = "What should change in the plan?"

function refineMessagesAt(
  messages: ThreadMessage[],
  refineRoundIndex: number
): {
  user?: Extract<ThreadMessage, { variant: "refine" }>
  assistant?: Extract<ThreadMessage, { variant: "refine_summary" }>
} {
  const i = 2 + 2 * refineRoundIndex
  const u = messages[i]
  const a = messages[i + 1]
  return {
    user:
      u?.role === "user" && u.variant === "refine"
        ? u
        : undefined,
    assistant:
      a?.role === "assistant" && a.variant === "refine_summary"
        ? a
        : undefined,
  }
}

function SnapshotGateBanner({
  gate,
  reduceMotion,
}: {
  gate: GateDTO
  reduceMotion: boolean
}) {
  const gateFired = Boolean(gate?.fired)
  if (gateFired) {
    return (
      <StudioShineBorder
        tone="amber"
        active={!reduceMotion}
        innerClassName="p-1"
      >
        <GateAlert gate={gate} embedded />
      </StudioShineBorder>
    )
  }
  return (
    <div className="rounded-2xl border border-slate-700/50 bg-slate-800 px-4 py-3 text-sm text-slate-100 backdrop-blur-md">
      No blocking gate on this version.
    </div>
  )
}

function EarlierPlanBlock({
  snapshot,
  exchange,
  reduceMotion,
}: {
  snapshot: PlanVersionSnapshot
  exchange: ReturnType<typeof refineMessagesAt>
  reduceMotion: boolean
}) {
  return (
    <div className="space-y-5 opacity-95">
      <p className="text-xs font-medium text-slate-400">
        Earlier version · v{snapshot.version}
      </p>
      <SnapshotGateBanner gate={snapshot.gate} reduceMotion={reduceMotion} />
      <PlanReportView report={snapshot.report} gate={snapshot.gate} />
      <PlanRefineExchange
        userMsg={exchange.user}
        assistantMsg={exchange.assistant}
      />
    </div>
  )
}

export function PlanPage() {
  const reduceMotion = usePrefersReducedMotion()
  const prdInputRef = useRef<HTMLInputElement>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const {
    phase,
    sessionId,
    report,
    gate,
    brief,
    setBrief,
    refineText,
    setRefineText,
    error,
    setError,
    agentFailed,
    clearAgentFailed,
    generate,
    refine,
    approve,
    startNewPlan,
    canSubmit,
    canRefine,
    minBriefLength,
    effectiveInputLength,
    bootstrapSession,
    messages,
    sessionSummaries,
    switchSession,
    sessionSwitching,
    prdText,
    prdFileLabel,
    prdBusy,
    loadPrdFile,
    clearPrd,
    planSnapshots,
    planVersion,
  } = useReportWorkflow()

  // Initial session only — do not re-run when sessionId changes or "New plan" races with a second POST /sessions.
  useEffect(() => {
    void bootstrapSession()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional: one-shot session bootstrap
  }, [])

  const gateFired = Boolean(gate?.fired)
  const busy =
    phase === "GENERATING" ||
    phase === "REFINING" ||
    sessionSwitching

  const showBriefComposer = phase === "IDLE"
  const showRefineComposer = phase === "REVIEW"
  const showFloatingComposer = showBriefComposer || showRefineComposer

  const showPlanStack =
    (phase === "REFINING" || phase === "REVIEW" || phase === "APPROVED") &&
    report != null &&
    gate != null

  const chatHistory = useMemo((): ChatHistoryEntry[] => {
    const fromApi = sessionSummaries
    const inApi = sessionId
      ? fromApi.some((s) => s.session_id === sessionId)
      : true
    const draft: ChatHistoryEntry[] =
      sessionId && !inApi
        ? [
            {
              session_id: sessionId,
              report_count: 0,
              updated_at: Math.floor(Date.now() / 1000),
              preview:
                brief.trim() || prdText.trim()
                  ? (brief.trim() || "(PRD only)").slice(0, 120)
                  : "New chat - not saved yet",
              isLocalDraft: true,
            },
          ]
        : []
    return [...draft, ...fromApi]
  }, [sessionSummaries, sessionId, brief, prdText])

  return (
    <div
      className="min-h-dvh bg-[#f4f6f9] text-slate-800"
      style={{
        backgroundImage:
          "radial-gradient(ellipse 110% 55% at 65% -5%, rgba(245,195,150,0.22), transparent 50%), radial-gradient(ellipse 70% 40% at 5% 90%, rgba(200,185,230,0.12), transparent 50%)",
      }}
    >
      <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-[#f4f6f9]/90 backdrop-blur-xl">
        <div className="flex items-center justify-between gap-4 px-4 py-3 lg:px-5">
          <Link
            to="/"
            className="font-semibold tracking-[0.18em] text-xs text-slate-900 hover:text-slate-600 lg:text-sm"
          >
            PLANR
          </Link>
          <div
            className="h-8 w-8 rounded-full border border-slate-200 bg-slate-100"
            aria-hidden
          />
        </div>
      </header>

      <input
        ref={prdInputRef}
        type="file"
        accept={PRD_ACCEPT}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0] ?? null
          void loadPrdFile(f)
          e.target.value = ""
        }}
      />

      <div className="flex min-h-[calc(100dvh-3.25rem)] flex-col lg:flex-row">
        <PlanSidebar
          open={sidebarOpen}
          onToggle={() => setSidebarOpen((v) => !v)}
          chats={chatHistory}
          activeSessionId={sessionId}
          onSelectSession={switchSession}
          sessionSwitching={sessionSwitching}
          onNewPlan={startNewPlan}
          newPlanDisabled={busy}
        />

        <div className="relative flex min-h-[min(100dvh,720px)] min-w-0 flex-1 flex-col lg:min-h-[calc(100dvh-3.25rem)]">
          <div className="relative z-[1] flex min-h-0 flex-1 flex-col">
            <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-44 pt-6 sm:px-8 sm:pb-48 sm:pt-10">
              {error ? (
                <div className="mb-6 shrink-0 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {agentFailed ? (
                    <>
                      The AI couldn&apos;t produce a valid plan after 3 attempts. Check your brief or{" "}
                      <button
                        type="button"
                        className="underline"
                        onClick={() => {
                          setError(null)
                          clearAgentFailed()
                          void generate()
                        }}
                      >
                        try again
                      </button>
                      .
                    </>
                  ) : (
                    <>
                      {error}
                      <button
                        type="button"
                        className="ml-2 underline"
                        onClick={() => setError(null)}
                      >
                        Dismiss
                      </button>
                    </>
                  )}
                </div>
              ) : null}

              {phase === "IDLE" && messages.length === 0 ? (
                <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-2 py-8 sm:py-12">
                  <div className="mx-auto flex max-w-lg flex-col items-center text-center">
                    <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-[1.25rem] border border-slate-200 bg-white/80 shadow-sm backdrop-blur-xl">
                      <Sparkles
                        className="h-7 w-7 text-slate-500"
                        strokeWidth={1.25}
                      />
                    </div>
                    <h1 className="text-2xl font-medium tracking-tight text-slate-900 sm:text-[1.75rem]">
                      {!brief.trim() && !prdText.trim() && sessionSummaries.length === 0
                        ? "Start a plan"
                        : "Let\u2019s shape your plan"}
                    </h1>
                    <p className="mt-3 text-sm leading-relaxed text-slate-500">
                      {!brief.trim() && !prdText.trim() && sessionSummaries.length === 0
                        ? "Paste a brief or upload a PRD and we\u2019ll produce a structured PM plan you can refine, approve, or export."
                        : "Add context below or attach a PRD and we\u2019ll produce a structured PM plan you can refine, approve, or re-run from the same PRD."}
                    </p>
                  </div>
                </div>
              ) : null}

              {phase === "IDLE" && messages.length > 0 ? (
                <p className="mx-auto mb-4 max-w-lg text-center text-sm text-slate-500">
                  Edit your brief or PRD, then send to run again.
                </p>
              ) : null}

              {phase === "GENERATING" ? (
                <div className="mx-auto w-full max-w-sm py-8 sm:max-w-md">
                  <PlanWorkingLoader
                    mode="generate"
                    reduceMotion={reduceMotion}
                  />
                </div>
              ) : null}

              {showPlanStack && report && gate ? (
                <div className="mx-auto w-full max-w-4xl space-y-10">
                  {(() => {
                    const briefMsg = messages[0]
                    if (!briefMsg || briefMsg.role !== "user" || briefMsg.variant !== "brief") return null
                    return (
                      <div className="flex justify-end">
                        <div className="max-w-[85%] rounded-2xl border border-slate-200 bg-slate-800 px-4 py-3 text-sm leading-relaxed text-slate-50 shadow-sm">
                          {briefMsg.prdAttachment && (
                            <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-300">
                              + {briefMsg.prdAttachment.filename}
                            </p>
                          )}
                          <p className="whitespace-pre-wrap">{briefMsg.content}</p>
                        </div>
                      </div>
                    )
                  })()}

                  {planSnapshots.map((snap, j) => (
                    <EarlierPlanBlock
                      key={`snap-${snap.version}-${j}`}
                      snapshot={snap}
                      exchange={refineMessagesAt(messages, j)}
                      reduceMotion={reduceMotion}
                    />
                  ))}

                  <div
                    className={
                      planSnapshots.length > 0
                        ? "space-y-5 border-t border-slate-700/50 pt-10"
                        : "space-y-5"
                    }
                  >
                    <p className="text-xs font-medium text-slate-400">
                      {planSnapshots.length > 0 ? "Current plan" : "Plan"} · v
                      {planVersion}
                    </p>
                    {gateFired ? (
                      <StudioShineBorder
                        tone="amber"
                        active={!reduceMotion}
                        innerClassName="p-1"
                      >
                        <GateAlert gate={gate} embedded />
                      </StudioShineBorder>
                    ) : (
                      <div className="rounded-2xl border border-slate-700/50 bg-slate-800 px-4 py-3 text-sm text-slate-100 backdrop-blur-md">
                        No blocking gate. Use Refine below to iterate, or start
                        over to run again from scratch.
                      </div>
                    )}

                    <PlanReportView report={report} gate={gate} />

                    {phase === "REFINING" ? (
                      <>
                        <PlanRefineExchange
                          userMsg={
                            refineMessagesAt(messages, planSnapshots.length).user
                          }
                          assistantMsg={undefined}
                        />
                        <div className="mx-auto w-full max-w-sm sm:max-w-md">
                          <PlanWorkingLoader
                            mode="refine"
                            reduceMotion={reduceMotion}
                          />
                        </div>
                      </>
                    ) : null}

                    {phase === "REVIEW" || phase === "APPROVED" ? (
                      <>
                        <details className="group rounded-2xl border border-slate-700/50 bg-slate-800 backdrop-blur-md open:bg-slate-800">
                          <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-slate-200 marker:content-none [&::-webkit-details-marker]:hidden">
                            <ChevronDown className="h-4 w-4 shrink-0 transition group-open:rotate-180" />
                            Raw JSON
                          </summary>
                          <pre className="max-h-[min(50vh,420px)] overflow-auto border-t border-slate-700/50 p-3 text-[11px] leading-relaxed text-slate-300">
                            {JSON.stringify(report, null, 2)}
                          </pre>
                        </details>

                        {phase === "REVIEW" && (
                          <div className="space-y-4">
                            <p className="mx-auto max-w-xl text-center text-xs leading-relaxed text-slate-400">
                              <span className="text-slate-600">Refine</span>: use
                              the composer below for human-in-the-loop feedback.{" "}
                              <span className="text-slate-600">Approve</span>:
                              record sign-off for this plan.{" "}
                              {gateFired ? (
                                <>
                                  A blocking gate is shown above; approving
                                  still logs your decision.{" "}
                                </>
                              ) : null}
                              <span className="text-slate-600">Start over</span>:
                              start a fresh session from scratch.
                            </p>
                            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-center">
                              <Button
                                type="button"
                                disabled={busy}
                                onClick={() => void approve()}
                              >
                                Approve
                              </Button>
                              <Button
                                type="button"
                                variant="outline"
                                disabled={busy}
                                onClick={() => void startNewPlan()}
                              >
                                Start over
                              </Button>
                            </div>
                          </div>
                        )}

                        {phase === "APPROVED" && (
                          <>
                            <div className="rounded-2xl border border-slate-700/50 bg-slate-800 px-4 py-3 text-center text-sm text-slate-100 backdrop-blur-md">
                              Plan approved for this session.
                            </div>
                            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-center">
                              <Button
                                type="button"
                                onClick={() => {
                                  void navigator.clipboard.writeText(
                                    JSON.stringify(report, null, 2)
                                  )
                                }}
                              >
                                Copy JSON
                              </Button>
                              <Button
                                type="button"
                                variant="outline"
                                onClick={() => {
                                  const blob = new Blob(
                                    [JSON.stringify(report, null, 2)],
                                    { type: "application/json" }
                                  )
                                  const url = URL.createObjectURL(blob)
                                  const a = document.createElement("a")
                                  a.href = url
                                  a.download = "plan.json"
                                  a.click()
                                  URL.revokeObjectURL(url)
                                }}
                              >
                                Download JSON
                              </Button>
                            </div>
                          </>
                        )}
                      </>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </div>

            {showFloatingComposer ? (
              <div className="pointer-events-none absolute inset-x-0 bottom-0 z-30 bg-gradient-to-t from-[#f4f6f9] via-[#f4f6f9]/90 to-transparent pb-5 pt-16">
                <div className="pointer-events-auto relative flex justify-center px-4">
                  {showBriefComposer ? (
                    <PlanFloatingComposer
                      variant="brief"
                      value={brief}
                      onChange={setBrief}
                      onSubmit={() => void generate()}
                      canSubmit={canSubmit}
                      sendLocked={prdBusy}
                      uploadLocked={prdBusy}
                      placeholder={BRIEF_PLACEHOLDER}
                      reduceMotion={reduceMotion}
                      prdFileLabel={prdFileLabel}
                      prdBusy={prdBusy}
                      onPickPrd={() => prdInputRef.current?.click()}
                      onClearPrd={clearPrd}
                      showPrd
                      footerHint={`${effectiveInputLength} / ${minBriefLength} chars (brief + PRD) · Send when ready`}
                    />
                  ) : (
                    <PlanFloatingComposer
                      variant="refine"
                      value={refineText}
                      onChange={setRefineText}
                      onSubmit={() => void refine()}
                      canSubmit={canRefine}
                      placeholder={REFINE_PLACEHOLDER}
                      reduceMotion={reduceMotion}
                      showPrd={false}
                      footerHint="Enter to send · Shift+Enter for newline"
                    />
                  )}
                </div>
              </div>
            ) : null}

            {phase === "APPROVED" ? (
              <div className="absolute bottom-6 left-0 right-0 z-10 flex justify-center px-4">
                <Button
                  type="button"
                  onClick={() => void startNewPlan()}
                >
                  Start new plan
                </Button>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
