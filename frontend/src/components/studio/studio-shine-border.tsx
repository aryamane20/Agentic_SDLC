import * as React from "react"

import { cn } from "@/lib/utils"

type Tone = "default" | "amber"

/**
 * Shine-border treatment — animated gradient rim (Magic UI–style, no extra deps).
 */
export function StudioShineBorder({
  children,
  className,
  innerClassName,
  tone = "default",
  active = true,
}: {
  children: React.ReactNode
  className?: string
  innerClassName?: string
  tone?: Tone
  /** Pause motion for reduced-motion users via parent. */
  active?: boolean
}) {
  const rim =
    tone === "amber"
      ? "from-amber-500/50 via-white/35 to-amber-600/40"
      : "from-zinc-500 via-white/25 to-zinc-600"

  return (
    <div
      className={cn(
        "rounded-xl bg-gradient-to-r p-px",
        rim,
        active && "animate-studio-shine bg-[length:200%_100%]",
        !active && "bg-[length:200%_100%]",
        className
      )}
    >
      <div
        className={cn(
          "rounded-[11px] bg-zinc-950/85 backdrop-blur-xl",
          innerClassName
        )}
      >
        {children}
      </div>
    </div>
  )
}
