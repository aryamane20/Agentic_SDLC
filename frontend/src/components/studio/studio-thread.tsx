import { motion } from "motion/react"

import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion"
import { cn } from "@/lib/utils"
import type { ThreadMessage } from "@/types/plan"

function Bubble({
  children,
  role,
  className,
}: {
  children: React.ReactNode
  role: "user" | "assistant"
  className?: string
}) {
  return (
    <div
      className={cn(
        "max-w-[95%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-lg",
        role === "user"
          ? "ml-auto border border-zinc-700/80 bg-zinc-900/90 text-zinc-100"
          : "mr-auto border border-zinc-700/60 bg-black/50 text-zinc-200",
        className
      )}
    >
      {children}
    </div>
  )
}

export function StudioThread({
  messages,
  className,
}: {
  messages: ThreadMessage[]
  className?: string
}) {
  const reduceMotion = usePrefersReducedMotion()

  return (
    <div
      className={cn(
        "flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1",
        className
      )}
    >
      {messages.length === 0 ? (
        <p className="text-center text-sm text-zinc-400">
          Submit a brief to start. The thread will show each turn here.
        </p>
      ) : null}
      {messages.map((msg, index) => {
        const animated = !reduceMotion
        const delay = Math.min(index * 0.05, 0.35)

        const wrap = (node: React.ReactNode) =>
          animated ? (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 14, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{
                delay,
                duration: 0.38,
                ease: [0.22, 1, 0.36, 1],
              }}
            >
              {node}
            </motion.div>
          ) : (
            <div key={msg.id}>{node}</div>
          )

        if (msg.role === "user") {
          return wrap(
            <Bubble role="user">
                <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-400">
                {msg.variant === "brief" ? "Brief" : "Refine"}
              </span>
              {msg.variant === "brief" && msg.prdAttachment ? (
                <p className="mt-1 text-[11px] text-zinc-400">
                  PRD attached: {msg.prdAttachment.filename} (
                  {msg.prdAttachment.excerptChars.toLocaleString()} chars)
                </p>
              ) : null}
              <p className="mt-1 whitespace-pre-wrap">{msg.content}</p>
            </Bubble>
          )
        }

        if (msg.variant === "plan_ready") {
          return wrap(
            <Bubble role="assistant">
              <p className="font-medium text-white">
                Plan v{msg.version} is ready.
              </p>
              <p className="mt-1 text-zinc-300">
                {msg.gateFired
                  ? "Approval gate fired — review reasons and the full plan."
                  : "No blocking gate. You can refine anytime or start over."}
              </p>
            </Bubble>
          )
        }

        return wrap(
          <Bubble role="assistant" className="font-mono text-xs">
            <p className="font-sans text-sm font-semibold text-white">
              {msg.title}
            </p>
            <pre className="mt-2 whitespace-pre-wrap text-zinc-300">
              {msg.lines.join("\n")}
            </pre>
          </Bubble>
        )
      })}
    </div>
  )
}
