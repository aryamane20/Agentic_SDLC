import { Home, PanelLeftClose, PanelLeft, Plus } from "lucide-react"
import { Link } from "react-router-dom"

import { cn } from "@/lib/utils"
import type { ChatHistoryEntry } from "@/types/plan"

function formatChatWhen(ts: number): string {
  try {
    return new Date(ts * 1000).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return ""
  }
}

export function PlanSidebar({
  open,
  onToggle,
  chats,
  activeSessionId,
  onSelectSession,
  sessionSwitching,
  onNewPlan,
  newPlanDisabled,
}: {
  open: boolean
  onToggle: () => void
  chats: ChatHistoryEntry[]
  activeSessionId: string | null
  onSelectSession: (sessionId: string) => void
  sessionSwitching?: boolean
  onNewPlan: () => void
  newPlanDisabled?: boolean
}) {
  return (
    <aside
      className={cn(
        "flex max-h-[min(42vh,280px)] shrink-0 flex-col border-slate-200/70 bg-white/70 backdrop-blur-xl transition-[width] duration-200 ease-out",
        "border-b lg:max-h-none lg:h-[calc(100dvh-3.25rem)] lg:border-b-0 lg:border-r",
        open ? "w-full lg:w-[272px]" : "w-full lg:w-[4.25rem]"
      )}
    >
      <div
        className={cn(
          "flex items-center gap-2 border-b border-slate-200/60 px-3 py-3",
          !open && "lg:flex-col lg:items-center lg:gap-3 lg:px-2 lg:py-4"
        )}
      >
        <button
          type="button"
          onClick={onToggle}
          className={cn(
            "rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800",
            "hidden lg:flex"
          )}
          aria-expanded={open}
          aria-label={open ? "Collapse sidebar" : "Expand sidebar"}
        >
          {open ? (
            <PanelLeftClose className="h-5 w-5" />
          ) : (
            <PanelLeft className="h-5 w-5" />
          )}
        </button>
        {open ? (
          <span className="text-sm font-semibold tracking-tight text-slate-800">
            PLANR
          </span>
        ) : null}
      </div>

      <div
        className={cn(
          "flex min-h-0 flex-1 flex-col gap-1 px-2 py-3",
          !open && "lg:items-center lg:px-1"
        )}
      >
        <button
          type="button"
          onClick={() => void onNewPlan()}
          disabled={newPlanDisabled}
          className={cn(
            "flex items-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-3 py-2.5 text-left text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 disabled:opacity-45",
            !open && "lg:w-10 lg:justify-center lg:px-0 lg:py-2.5"
          )}
        >
          <Plus className="h-4 w-4 shrink-0" aria-hidden />
          {open ? <span>New plan</span> : null}
        </button>

        <Link
          to="/"
          className={cn(
            "flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-100 hover:text-slate-900",
            !open && "lg:w-10 lg:justify-center lg:px-0"
          )}
        >
          <Home className="h-4 w-4 shrink-0" aria-hidden />
          {open ? <span>Home</span> : null}
        </Link>

        {open ? (
          <>
            <p className="mt-4 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400">
              Your plans
            </p>
            <ul className="mt-1 min-h-0 flex-1 space-y-0.5 overflow-y-auto pr-1">
              {chats.length === 0 ? (
                <li className="px-2 py-2 text-xs text-slate-400">
                  Saved plans for this browser show up after you run{" "}
                  <span className="text-slate-600">Generate</span>. Use{" "}
                  <span className="text-slate-600">New plan</span> for another
                  initiative.
                </li>
              ) : (
                chats.map((c) => {
                  const active = c.session_id === activeSessionId
                  const rowKey = c.isLocalDraft
                    ? `${c.session_id}-draft`
                    : c.session_id
                  return (
                    <li key={rowKey}>
                      <button
                        type="button"
                        disabled={sessionSwitching}
                        onClick={() => void onSelectSession(c.session_id)}
                        className={cn(
                          "w-full rounded-lg border px-2 py-2 text-left transition disabled:opacity-45",
                          active
                            ? "border-slate-300 bg-slate-100 text-slate-900 font-medium"
                            : "border-transparent text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
                        )}
                      >
                        <span
                          className="block truncate text-xs leading-snug"
                          title={c.preview}
                        >
                          {c.preview}
                        </span>
                        <span className="mt-0.5 block font-mono text-[10px] text-slate-400">
                          {c.isLocalDraft ? (
                            <span className="text-amber-600">draft</span>
                          ) : (
                            <>
                              {formatChatWhen(c.updated_at)}
                              {c.report_count > 0 && (
                                <span className="text-slate-300">
                                  {" "}
                                  · {c.report_count} plan
                                  {c.report_count === 1 ? "" : "s"}
                                </span>
                              )}
                            </>
                          )}
                        </span>
                      </button>
                    </li>
                  )
                })
              )}
            </ul>
          </>
        ) : (
          <div className="hidden flex-1 lg:block" aria-hidden />
        )}
      </div>
    </aside>
  )
}
