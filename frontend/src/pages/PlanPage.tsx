import { useEffect, useMemo, useRef, useState } from "react"
import { ChevronDown, Sparkles } from "lucide-react"
import { Link } from "react-router-dom"

import { GateAlert } from "@/components/plan/gate-alert"
import { PlanFloatingComposer } from "@/components/plan/plan-floating-composer"
import { PlanReportView } from "@/components/plan/plan-report-view"
import { PlanSidebar } from "@/components/plan/plan-sidebar"
import { PlanWorkingLoader } from "@/components/plan/plan-working-loader"
import { StudioShineBorder } from "@/components/studio/studio-shine-border"
import { Button } from "@/components/ui/button"
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion"
import { useReportWorkflow } from "@/hooks/use-report-workflow"
import { PRD_ACCEPT } from "@/lib/prd-upload"
import type { ChatHistoryEntry } from "@/types/plan"

const BRIEF_PLACEHOLDER = "Describe your initiative, or attach a PRD with +"
const REFINE_PLACEHOLDER = "What should change in the plan?"

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
                  : "New chat — not saved yet",
              isLocalDraft: true,
            },
          ]
        : []
    return [...draft, ...fromApi]
  }, [sessionSummaries, sessionId, brief, prdText])

  return (
    <div
      className="min-h-dvh bg-black text-zinc-200"
      style={{
        backgroundImage:
          "radial-gradient(ellipse 140% 90% at 50% -25%, rgba(120,120,170,0.12), transparent 50%), radial-gradient(ellipse 80% 50% at 100% 50%, rgba(80,80,120,0.06), transparent 45%)",
      }}
    >
      <header className="sticky top-0 z-20 border-b border-zinc-800/60 bg-black/50 backdrop-blur-xl">
        <div className="flex items-center justify-between gap-4 px-4 py-3 lg:px-5">
          <Link
            to="/"
            className="font-semibold tracking-[0.18em] text-xs text-white hover:text-zinc-200 lg:text-sm"
          >
            PLANR
          </Link>
          <div
            className="h-8 w-8 rounded-full border border-zinc-700/50 bg-zinc-900/50"
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
                <div className="mb-6 shrink-0 rounded-xl border border-red-500/40 bg-red-950/35 px-3 py-2 text-sm text-red-200">
                  {error}
                  <button
                    type="button"
                    className="ml-2 underline"
                    onClick={() => setError(null)}
                  >
                    Dismiss
                  </button>
                </div>
              ) : null}

              {phase === "IDLE" && messages.length === 0 ? (
                <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-2 py-8 sm:py-12">
                  <div className="mx-auto flex max-w-lg flex-col items-center text-center">
                    <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-[1.25rem] border border-zinc-600/40 bg-zinc-900/30 shadow-[0_0_0_1px_rgba(255,255,255,0.04)] backdrop-blur-xl">
                      <Sparkles
                        className="h-7 w-7 text-zinc-200"
                        strokeWidth={1.25}
                      />
                    </div>
                    <h1 className="text-2xl font-medium tracking-tight text-white sm:text-[1.75rem]">
                      Let&apos;s shape your plan
                    </h1>
                    <p className="mt-3 text-sm leading-relaxed text-zinc-300">
                      Add context below or attach a PRD and we&apos;ll produce
                      a structured PM plan you can refine, approve, or re-run
                      from the same PRD.
                    </p>
                    <p className="mt-2 text-xs text-zinc-400">
                      (.txt, .md, .pdf, .docx · max 5 MB)
                    </p>
                  </div>
                </div>
              ) : null}

              {phase === "IDLE" && messages.length > 0 ? (
                <p className="mx-auto mb-4 max-w-lg text-center text-sm text-zinc-300">
                  Edit your brief or PRD, then send to run again.
                </p>
              ) : null}

              {(phase === "GENERATING" || phase === "REFINING") && (
                <div className="mx-auto w-full max-w-sm py-8 sm:max-w-md">
                  <PlanWorkingLoader
                    mode={phase === "GENERATING" ? "generate" : "refine"}
                    reduceMotion={reduceMotion}
                  />
                </div>
              )}

              {(phase === "REVIEW" || phase === "APPROVED") && report && gate ? (
                <div className="mx-auto w-full max-w-4xl space-y-5">
                  {gateFired ? (
                    <StudioShineBorder
                      tone="amber"
                      active={!reduceMotion}
                      innerClassName="p-1"
                    >
                      <GateAlert gate={gate} embedded />
                    </StudioShineBorder>
                  ) : (
                    <div className="rounded-2xl border border-zinc-800/70 bg-zinc-950/35 px-4 py-3 text-sm text-zinc-300 backdrop-blur-md">
                      No blocking gate — use Refine below to iterate, or start over
                      to run again with the same brief and PRD.
                    </div>
                  )}

                  <PlanReportView report={report} gate={gate} />

                  <details className="group rounded-2xl border border-zinc-800/70 bg-zinc-950/25 backdrop-blur-md open:bg-zinc-950/35">
                    <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-zinc-100 marker:content-none [&::-webkit-details-marker]:hidden">
                      <ChevronDown className="h-4 w-4 shrink-0 transition group-open:rotate-180" />
                      Raw JSON
                    </summary>
                    <pre className="max-h-[min(50vh,420px)] overflow-auto border-t border-zinc-800/70 p-3 text-[11px] leading-relaxed text-zinc-300">
                      {JSON.stringify(report, null, 2)}
                    </pre>
                  </details>

                  {phase === "REVIEW" && (
                    <div className="space-y-4">
                      <p className="mx-auto max-w-xl text-center text-xs leading-relaxed text-zinc-500">
                        <span className="text-zinc-300">Refine</span> — use the
                        composer below for human-in-the-loop feedback.{" "}
                        <span className="text-zinc-300">Approve</span> — record
                        sign-off for this plan.{" "}
                        {gateFired ? (
                          <>
                            A blocking gate is shown above; approving still logs
                            your decision.{" "}
                          </>
                        ) : null}
                        <span className="text-zinc-300">Start over</span> — new
                        session with the same brief and PRD so you can generate
                        again from scratch.
                      </p>
                      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-center">
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={busy}
                          onClick={() => void approve()}
                        >
                          Approve
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          className="text-zinc-300 hover:text-zinc-100"
                          disabled={busy}
                          onClick={() => void startNewPlan()}
                        >
                          Start over
                        </Button>
                      </div>
                    </div>
                  )}

                  {phase === "APPROVED" && (
                    <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 px-4 py-3 text-center text-sm text-emerald-100 backdrop-blur-md">
                      Plan approved for this session.
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {showFloatingComposer ? (
              <div className="pointer-events-none absolute inset-x-0 bottom-0 z-30 bg-gradient-to-t from-black via-black/90 to-transparent pb-5 pt-16">
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
                      footerHint="Enter — send · Shift+Enter — newline"
                    />
                  )}
                </div>
              </div>
            ) : null}

            {phase === "APPROVED" ? (
              <div className="absolute bottom-6 left-0 right-0 z-10 flex justify-center px-4">
                <Button
                  type="button"
                  variant="outline"
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
