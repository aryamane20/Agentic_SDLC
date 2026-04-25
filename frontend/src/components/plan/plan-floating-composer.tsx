import { ArrowUp, Loader2, Plus, X } from "lucide-react"
import { useEffect, useRef } from "react"

import { StudioShineBorder } from "@/components/studio/studio-shine-border"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type Variant = "brief" | "refine"

export function PlanFloatingComposer({
  variant,
  value,
  onChange,
  onSubmit,
  canSubmit,
  sendLocked,
  uploadLocked,
  placeholder,
  reduceMotion,
  prdFileLabel,
  prdBusy,
  onPickPrd,
  onClearPrd,
  showPrd,
  footerHint,
}: {
  variant: Variant
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  canSubmit: boolean
  sendLocked?: boolean
  uploadLocked?: boolean
  placeholder: string
  reduceMotion: boolean
  prdFileLabel?: string | null
  prdBusy?: boolean
  onPickPrd?: () => void
  onClearPrd?: () => void
  showPrd?: boolean
  footerHint?: string
}) {
  const ta = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = ta.current
    if (!el) return
    el.style.height = "0px"
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }, [value])

  const sendBlocked = !canSubmit || Boolean(sendLocked)

  return (
    <div className="w-full max-w-2xl">
      {showPrd && prdFileLabel ? (
        <div className="mb-2 flex justify-center">
          <span className="inline-flex max-w-full items-center gap-1 truncate rounded-full border border-slate-200 bg-white/90 px-3 py-1 text-[11px] text-slate-600 shadow-sm backdrop-blur-md">
            <span className="truncate">{prdFileLabel}</span>
            <button
              type="button"
              className="rounded-full p-0.5 text-slate-400 hover:text-slate-700"
              aria-label="Remove PRD"
              onClick={() => onClearPrd?.()}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </span>
        </div>
      ) : null}

      <StudioShineBorder
        active={!reduceMotion}
        className="rounded-[28px]"
        innerClassName="rounded-[27px] p-1.5"
      >
        <div
          className={cn(
            "flex items-end gap-1 rounded-[24px] bg-white/95 px-2 py-2 shadow-md"
          )}
        >
          {showPrd ? (
            <button
              type="button"
              disabled={Boolean(uploadLocked || prdBusy)}
              onClick={() => onPickPrd?.()}
              className={cn(
                "mb-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600 transition hover:border-slate-300 hover:bg-slate-100 hover:text-slate-800 disabled:opacity-40"
              )}
              aria-label="Attach PRD"
            >
              {prdBusy ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Plus className="h-5 w-5" strokeWidth={2} />
              )}
            </button>
          ) : null}

          <textarea
            ref={ta}
            rows={1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                if (!sendBlocked) onSubmit()
              }
            }}
            placeholder={placeholder}
            className="mb-1 max-h-[220px] min-h-[44px] flex-1 resize-none bg-transparent px-2 py-2.5 text-[15px] leading-relaxed text-slate-800 placeholder:text-slate-400 focus:outline-none"
          />

          <Button
            type="button"
            size="icon"
            disabled={sendBlocked}
            onClick={() => void onSubmit()}
            className={cn(
              "mb-0.5 h-10 w-10 shrink-0 rounded-full",
              sendBlocked && "opacity-40"
            )}
            aria-label={variant === "brief" ? "Submit brief" : "Send refine"}
          >
            <ArrowUp className="h-5 w-5" strokeWidth={2.25} />
          </Button>
        </div>
      </StudioShineBorder>

      {footerHint ? (
        <p className="mt-2 text-center text-[11px] text-slate-400 tabular-nums">
          {footerHint}
        </p>
      ) : null}
    </div>
  )
}
