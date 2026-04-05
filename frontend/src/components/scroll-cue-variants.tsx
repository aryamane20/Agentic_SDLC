import type { MouseEvent } from "react"
import { ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"

type AuroraProps = {
  /** Block navigation (e.g. showcase page). */
  demo?: boolean
  className?: string
}

function stopIfDemo(demo: boolean | undefined, e: MouseEvent<HTMLAnchorElement>) {
  if (demo) e.preventDefault()
}

/** Aurora glass pill: soft bloom + floaty chevron; links to `#about` unless `demo`. */
export function ScrollCueAuroraGlass({ demo, className }: AuroraProps) {
  return (
    <a
      href="#about"
      aria-label={demo ? undefined : "Scroll to What is PLANR"}
      onClick={(e) => stopIfDemo(demo, e)}
      className={cn(
        "group relative inline-flex touch-manipulation flex-col items-center outline-none",
        "focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 focus-visible:ring-offset-black",
        className,
      )}
    >
      <span
        aria-hidden
        className="absolute inset-0 rounded-full bg-gradient-to-br from-violet-500/35 via-transparent to-cyan-400/30 opacity-70 blur-lg motion-safe:transition-opacity motion-safe:duration-500 group-hover:opacity-100"
      />
      <span
        className={cn(
          "relative flex flex-col items-center gap-2 rounded-full border border-white/10",
          "bg-zinc-950/75 px-8 py-4 backdrop-blur-xl",
          "shadow-[0_0_48px_-18px_rgba(167,139,250,0.45)]",
          "motion-safe:transition motion-safe:duration-300 group-hover:scale-[1.03] group-hover:border-white/20",
        )}
      >
        <span className="text-xs font-medium uppercase tracking-[0.2em] text-zinc-300 motion-safe:transition-colors group-hover:text-white">
          What is PLANR
        </span>
        <ChevronDown
          className="h-5 w-5 text-zinc-300 motion-safe:animate-cue-float motion-safe:transition-colors group-hover:text-white"
          aria-hidden
        />
      </span>
    </a>
  )
}
