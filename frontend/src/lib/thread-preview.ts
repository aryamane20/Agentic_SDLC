import type { ThreadMessage } from "@/types/plan"

/** One-line label for sidebar “recents” (Claude-style). */
export function threadMessagePreview(msg: ThreadMessage): string {
  if (msg.role === "user") {
    if (msg.variant === "brief") {
      const base =
        msg.content === "(PRD only, see attachment)"
          ? "PRD upload"
          : msg.content.trim()
      const head = base.split(/\s+/).slice(0, 8).join(" ")
      return head.length > 52 ? `${head.slice(0, 52)}…` : head
    }
    const r = msg.content.trim()
    const h = r.length > 48 ? `${r.slice(0, 48)}…` : r
    return `Refine: ${h}`
  }
  if (msg.variant === "plan_ready") {
    return `Plan v${msg.version} ready${msg.gateFired ? " · gate" : ""}`
  }
  const t = msg.title.trim()
  return t.length > 56 ? `${t.slice(0, 56)}…` : t
}
