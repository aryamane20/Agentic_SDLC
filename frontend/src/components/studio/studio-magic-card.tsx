import * as React from "react"

import { cn } from "@/lib/utils"

/**
 * Magic-card style spotlight — radial highlight follows pointer (Studio glass).
 */
export function StudioMagicCard({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  const ref = React.useRef<HTMLDivElement>(null)

  const onMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    el.style.setProperty("--studio-mx", `${e.clientX - r.left}px`)
    el.style.setProperty("--studio-my", `${e.clientY - r.top}px`)
  }

  const onMouseLeave = () => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    el.style.setProperty("--studio-mx", `${r.width / 2}px`)
    el.style.setProperty("--studio-my", `${r.height / 2}px`)
  }

  return (
    <div
      ref={ref}
      className={cn(
        "group relative overflow-hidden rounded-2xl border border-zinc-800/80 bg-zinc-950/50 backdrop-blur-xl",
        className
      )}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      {...props}
    >
      <div
        className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        style={{
          background:
            "radial-gradient(520px circle at var(--studio-mx,50%) var(--studio-my,50%), rgba(255,255,255,0.07), transparent 55%)",
        }}
        aria-hidden
      />
      <div className="relative z-[1]">{children}</div>
    </div>
  )
}
