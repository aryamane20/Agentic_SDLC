import type { ReactNode } from "react"

import { cn } from "@/lib/utils"
import type { ThreadMessage } from "@/types/plan"

function Bubble({
  children,
  role,
  className,
}: {
  children: ReactNode
  role: "user" | "assistant"
  className?: string
}) {
  return (
    <div
      className={cn(
        "max-w-[95%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
        role === "user"
          ? "ml-auto border border-slate-200 bg-slate-800 text-slate-50"
          : "mr-auto border border-slate-200/80 bg-white/80 text-slate-700",
        className
      )}
    >
      {children}
    </div>
  )
}

type RefineUser = Extract<ThreadMessage, { variant: "refine" }>
type RefineSummary = Extract<ThreadMessage, { variant: "refine_summary" }>

export function PlanRefineExchange({
  userMsg,
  assistantMsg,
}: {
  userMsg: RefineUser | undefined
  assistantMsg: RefineSummary | undefined
}) {
  if (!userMsg && !assistantMsg) return null

  return (
    <div className="space-y-3 py-2">
      <p className="text-center text-[10px] font-medium uppercase tracking-wider text-slate-400">
        Feedback
      </p>
      {userMsg ? (
        <Bubble role="user">
          <span className="text-[10px] font-medium uppercase tracking-wider text-slate-300">
            Refine
          </span>
          <p className="mt-1 whitespace-pre-wrap">{userMsg.content}</p>
        </Bubble>
      ) : null}
      {assistantMsg ? (
        <Bubble role="assistant">
          <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
            {assistantMsg.title}
          </p>
          <ul className="mt-2 list-inside list-disc space-y-1 text-slate-600">
            {assistantMsg.lines.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </Bubble>
      ) : null}
    </div>
  )
}
