import { AlertTriangle } from "lucide-react"

import type { GateDTO } from "@/types/plan"

export function GateAlert({
  gate,
  embedded,
}: {
  gate: GateDTO
  /** When wrapped in StudioShineBorder — drop outer rim. */
  embedded?: boolean
}) {
  if (!gate.fired) return null

  return (
    <div
      className={
        embedded
          ? "rounded-[10px] bg-amber-950/35 px-4 py-3"
          : "rounded-lg border border-amber-500/40 bg-amber-950/40 px-4 py-3"
      }
      role="alert"
    >
      <div className="flex gap-2">
        <AlertTriangle
          className="mt-0.5 h-5 w-5 shrink-0 text-amber-400"
          strokeWidth={1.5}
          aria-hidden
        />
        <div>
          <p className="text-sm font-semibold text-amber-100">
            Approval gate fired
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-amber-100/90">
            {gate.reasons.length === 0 ? (
              <li>Review the plan and risks before sign-off.</li>
            ) : (
              gate.reasons.map((r, i) => {
                const text = typeof r === "string" ? r : String(r)
                return (
                  <li key={`${i}-${text.slice(0, 48)}`}>{text}</li>
                )
              })
            )}
          </ul>
        </div>
      </div>
    </div>
  )
}
