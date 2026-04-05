import { cn } from "@/lib/utils"

type Mode = "generate" | "refine"

const COPY: Record<Mode, string> = {
  generate: "Building your project plan — usually under 90 seconds.",
  refine: "Applying your feedback — usually under a minute.",
}

/**
 * Single-state loading UI: no step metaphor (the model is one request; we have no streamed phases).
 */
export function PlanWorkingLoader({
  mode,
  reduceMotion = false,
}: {
  mode: Mode
  reduceMotion?: boolean
}) {
  return (
    <div className="rounded-2xl border border-zinc-800/80 bg-zinc-950/80 px-6 py-8 text-center shadow-[0_0_0_1px_rgba(255,255,255,0.04)] backdrop-blur-md">
      <p className="font-semibold tracking-[0.18em] text-xs text-white">PLANR</p>
      <div className="mx-auto mt-5 h-1.5 w-full max-w-[220px] overflow-hidden rounded-full bg-zinc-800/90">
        <div
          className={cn(
            "h-full w-[42%] rounded-full bg-zinc-300",
            reduceMotion
              ? "mx-auto opacity-90"
              : "animate-plan-loader-indeterminate will-change-transform"
          )}
          aria-hidden
        />
      </div>
      <p className="mx-auto mt-5 max-w-sm text-sm leading-relaxed text-zinc-300">
        {COPY[mode]}
      </p>
      <p className="mt-3 text-xs text-zinc-500">
        Working — you can leave this tab open.
      </p>
    </div>
  )
}
