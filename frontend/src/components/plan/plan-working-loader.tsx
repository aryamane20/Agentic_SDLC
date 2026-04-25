import { cn } from "@/lib/utils"

type Mode = "generate" | "refine"

const COPY: Record<Mode, string> = {
  generate: "Building your project plan in under 90 seconds.",
  refine: "Applying your feedback in under a minute.",
}

export function PlanWorkingLoader({
  mode,
  reduceMotion = false,
}: {
  mode: Mode
  reduceMotion?: boolean
}) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white/80 px-6 py-8 text-center shadow-sm backdrop-blur-md">
      <p className="font-semibold tracking-[0.18em] text-xs text-slate-900">PLANR</p>
      <div className="mx-auto mt-5 h-1.5 w-full max-w-[220px] overflow-hidden rounded-full bg-slate-200">
        <div
          className={cn(
            "h-full w-[42%] rounded-full bg-slate-500",
            reduceMotion
              ? "mx-auto opacity-90"
              : "animate-plan-loader-indeterminate will-change-transform"
          )}
          aria-hidden
        />
      </div>
      <p className="mx-auto mt-5 max-w-sm text-sm leading-relaxed text-slate-600">
        {COPY[mode]}
      </p>
      <p className="mt-3 text-xs text-slate-400">
        Working...you can leave this tab open.
      </p>
    </div>
  )
}
