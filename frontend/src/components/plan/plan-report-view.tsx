import type { ReactNode } from "react"

import {
  ASSUMPTION_TABLE,
  formatAssumptionRiskIfWrong,
  formatAssumptionWhyBasis,
  getMetadataObject,
  getPmConfidence,
  METADATA_PILL_FIELDS,
  METADATA_TEXT_FIELDS,
  OPEN_QUESTION_FIELDS,
  PHASE_FIELDS,
  PLAN_CRITICAL_PATH_KEY,
  PLAN_REPORT_ROOT,
  PLAN_SECTIONS,
  PLAN_SUMMARY_PILLS,
  PROJECT_PLAN_FIELDS,
  PM_CONFIDENCE_PILL,
  PROJECT_CONTEXT_FIELDS,
  PROJECT_CONTEXT_QUOTES_FIELD,
  RISK_TABLE,
  STAFFING_TABLE,
  TASK_TABLE,
  UI_LABELS,
} from "@/lib/plan-display-profile"
import type { GateDTO, ReportRecord } from "@/types/plan"

function str(v: unknown): string {
  if (v == null) return ""
  if (typeof v === "string") return v
  if (typeof v === "number" || typeof v === "boolean") return String(v)
  return JSON.stringify(v)
}

function Pill({
  children,
  tone = "neutral",
}: {
  children: ReactNode
  tone?: "neutral" | "blue" | "amber" | "emerald" | "rose"
}) {
  const cls =
    tone === "blue"
      ? "border-blue-500/35 bg-blue-950/40 text-blue-100"
      : tone === "amber"
        ? "border-amber-500/35 bg-amber-950/35 text-amber-100"
        : tone === "emerald"
          ? "border-emerald-500/30 bg-emerald-950/30 text-emerald-100"
          : tone === "rose"
            ? "border-rose-500/35 bg-rose-950/35 text-rose-100"
            : "border-zinc-600/50 bg-zinc-900/60 text-zinc-200"
  return (
    <span
      className={`inline-flex max-w-full items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${cls}`}
    >
      {children}
    </span>
  )
}

function Section({
  id,
  title,
  children,
}: {
  id?: string
  title: string
  children: ReactNode
}) {
  return (
    <section
      id={id}
      className="rounded-2xl border border-zinc-800/70 bg-zinc-950/30 backdrop-blur-md"
    >
      <h2 className="border-b border-zinc-800/60 px-4 py-3 text-sm font-semibold tracking-tight text-white">
        {title}
      </h2>
      <div className="p-4">{children}</div>
    </section>
  )
}

function Th({
  children,
  className = "",
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <th
      className={`border-b border-zinc-700/60 bg-zinc-900/40 px-2 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-zinc-400 ${className}`}
    >
      {children}
    </th>
  )
}

function Td({
  children,
  className = "",
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <td
      className={`border-b border-zinc-800/50 px-2 py-2 align-top text-xs text-zinc-300 ${className}`}
    >
      {children}
    </td>
  )
}

export function PlanReportView({
  report,
  gate,
}: {
  report: ReportRecord
  gate?: GateDTO | null
}) {
  const parseErr = report[PLAN_REPORT_ROOT.parseError]
  const meta = getMetadataObject(report)
  const pm = getPmConfidence(report)

  const understanding = report[PLAN_REPORT_ROOT.projectUnderstanding] as
    | Record<string, unknown>
    | undefined
  const assumptionLog: unknown[] = Array.isArray(
    report[PLAN_REPORT_ROOT.assumptionLog]
  )
    ? (report[PLAN_REPORT_ROOT.assumptionLog] as unknown[])
    : []
  const projectPlan = report[PLAN_REPORT_ROOT.projectPlan] as
    | Record<string, unknown>
    | undefined
  const phases: unknown[] = Array.isArray(
    projectPlan?.[PROJECT_PLAN_FIELDS.phases]
  )
    ? (projectPlan[PROJECT_PLAN_FIELDS.phases] as unknown[])
    : []
  const riskRegister: unknown[] = Array.isArray(
    report[PLAN_REPORT_ROOT.riskRegister]
  )
    ? (report[PLAN_REPORT_ROOT.riskRegister] as unknown[])
    : []
  const staffing: unknown[] = Array.isArray(
    report[PLAN_REPORT_ROOT.staffingPlan]
  )
    ? (report[PLAN_REPORT_ROOT.staffingPlan] as unknown[])
    : []
  const openQs: unknown[] = Array.isArray(
    report[PLAN_REPORT_ROOT.openQuestions]
  )
    ? (report[PLAN_REPORT_ROOT.openQuestions] as unknown[])
    : []
  const viability = report[PLAN_REPORT_ROOT.projectViability] as
    | Record<string, unknown>
    | undefined

  const criticalPath = projectPlan?.[PLAN_CRITICAL_PATH_KEY] as
    | Record<string, unknown>
    | undefined

  return (
    <div className="space-y-5">
      {parseErr != null ? (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/25 px-3 py-2 text-xs text-rose-100">
          <p className="font-medium">{UI_LABELS.parseWarningTitle}</p>
          <p className="mt-1 whitespace-pre-wrap text-rose-100/90">{str(parseErr)}</p>
        </div>
      ) : null}

      {gate?.fired ? (
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone="amber">{UI_LABELS.gateBlocking}</Pill>
          <span className="text-[11px] text-zinc-500">
            {UI_LABELS.gateBlockingHint}
          </span>
        </div>
      ) : gate != null ? (
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone="emerald">{UI_LABELS.gateClear}</Pill>
        </div>
      ) : null}

      <Section
        id={PLAN_SECTIONS.metadata.id}
        title={PLAN_SECTIONS.metadata.title}
      >
        <div className="flex flex-wrap gap-2">
          {METADATA_PILL_FIELDS.map(({ field, prefix, tone }) => {
            const val = meta?.[field]
            if (val == null) return null
            const text = prefix ? `${prefix}${str(val)}` : str(val)
            return (
              <Pill key={field} tone={tone}>
                {text}
              </Pill>
            )
          })}
          {pm.score != null ? (
            <Pill tone={PM_CONFIDENCE_PILL.tone}>
              {PM_CONFIDENCE_PILL.prefix}
              {str(pm.score)}
            </Pill>
          ) : null}
        </div>
        {meta?.[METADATA_TEXT_FIELDS.generatedAt] != null ? (
          <p className="mt-2 text-xs text-zinc-500">
            Generated: {str(meta[METADATA_TEXT_FIELDS.generatedAt])}
          </p>
        ) : null}
        {meta?.[METADATA_TEXT_FIELDS.sdlcRationale] != null ? (
          <p className="mt-3 text-sm leading-relaxed text-zinc-300">
            {str(meta[METADATA_TEXT_FIELDS.sdlcRationale])}
          </p>
        ) : null}
        {pm.interpretation ? (
          <p className="mt-2 text-xs leading-relaxed text-zinc-400">
            {pm.interpretation}
          </p>
        ) : null}
      </Section>

      {understanding &&
      Object.keys(understanding).some((k) => understanding[k] != null) ? (
        <Section
          id={PLAN_SECTIONS.projectContext.id}
          title={PLAN_SECTIONS.projectContext.title}
        >
          <dl className="grid gap-3 sm:grid-cols-1">
            {PROJECT_CONTEXT_FIELDS.map(({ field, label }) => {
              const val = understanding[field]
              if (val == null || val === "") return null
              return (
                <div key={field}>
                  <dt className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
                    {label}
                  </dt>
                  <dd className="mt-0.5 text-sm text-zinc-200">{str(val)}</dd>
                </div>
              )
            })}
          </dl>
          {Array.isArray(understanding[PROJECT_CONTEXT_QUOTES_FIELD]) &&
          (understanding[PROJECT_CONTEXT_QUOTES_FIELD] as unknown[]).length >
            0 ? (
            <div className="mt-4">
              <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
                {UI_LABELS.supportingQuotes}
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-zinc-400">
                {(
                  understanding[PROJECT_CONTEXT_QUOTES_FIELD] as unknown[]
                ).map((q, i) => (
                  <li key={i}>{str(q)}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </Section>
      ) : null}

      <Section
        id={PLAN_SECTIONS.assumptions.id}
        title={PLAN_SECTIONS.assumptions.title}
      >
        {assumptionLog.length === 0 ? (
          <p className="text-sm text-zinc-500">{UI_LABELS.emptyAssumptions}</p>
        ) : (
          <div className="-mx-4 overflow-x-auto sm:mx-0">
            <table className="w-full min-w-[640px] border-collapse text-left">
              <thead>
                <tr>
                  {ASSUMPTION_TABLE.headers.map((h) => (
                    <Th key={h}>{h}</Th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {assumptionLog.map((row, i) => {
                  const o =
                    row && typeof row === "object" && !Array.isArray(row)
                      ? (row as Record<string, unknown>)
                      : {}
                  return (
                    <tr key={str(o.id) || i}>
                      <Td className="whitespace-nowrap font-mono text-[11px] text-zinc-400">
                        {o.id != null ? str(o.id) : "—"}
                      </Td>
                      <Td>{o.what != null ? str(o.what) : "—"}</Td>
                      <Td className="max-w-[200px]">
                        {formatAssumptionWhyBasis(o)}
                      </Td>
                      <Td className="max-w-[200px]">
                        {formatAssumptionRiskIfWrong(o)}
                      </Td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section id={PLAN_SECTIONS.plan.id} title={PLAN_SECTIONS.plan.title}>
        {!projectPlan ? (
          <p className="text-sm text-zinc-500">{UI_LABELS.emptyPlan}</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              {PLAN_SUMMARY_PILLS.map(({ field, prefix, suffix }) => {
                const val = projectPlan[field]
                if (val == null) return null
                return (
                  <Pill key={field}>
                    {prefix}
                    {str(val)}
                    {suffix}
                  </Pill>
                )
              })}
            </div>
            {criticalPath &&
            Object.keys(criticalPath).some((k) => criticalPath[k] != null) ? (
              <div className="mt-4 rounded-lg border border-zinc-800/60 bg-zinc-900/25 p-3 text-xs text-zinc-300">
                <p className="font-medium text-zinc-200">
                  {UI_LABELS.criticalPathHeading}
                </p>
                <ul className="mt-2 space-y-1">
                  {Object.entries(criticalPath).map(([k, v]) =>
                    v != null && str(v) !== "" ? (
                      <li key={k}>
                        <span className="text-zinc-500">{k}: </span>
                        {str(v)}
                      </li>
                    ) : null
                  )}
                </ul>
              </div>
            ) : null}

            <div className="mt-4 space-y-2">
              {phases.length === 0 ? (
                <p className="text-sm text-zinc-500">{UI_LABELS.emptyPhases}</p>
              ) : (
                phases.map((ph, pi) => {
                  const p =
                    ph && typeof ph === "object" && !Array.isArray(ph)
                      ? (ph as Record<string, unknown>)
                      : {}
                  const tasks: unknown[] = Array.isArray(p[PHASE_FIELDS.tasks])
                    ? (p[PHASE_FIELDS.tasks] as unknown[])
                    : []
                  const milestones: unknown[] = Array.isArray(
                    p[PHASE_FIELDS.milestones]
                  )
                    ? (p[PHASE_FIELDS.milestones] as unknown[])
                    : []
                  const phaseNum = p[PHASE_FIELDS.phaseNumber]
                  return (
                    <details
                      key={pi}
                      className="group rounded-xl border border-zinc-800/60 bg-zinc-900/20 open:bg-zinc-900/30"
                    >
                      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-2 gap-y-1 px-3 py-2 text-sm font-medium text-zinc-100 marker:content-none [&::-webkit-details-marker]:hidden">
                        <span className="text-zinc-400">
                          Phase {str(phaseNum ?? pi + 1)}
                        </span>
                        {p[PHASE_FIELDS.name] != null ? (
                          <span className="text-white">
                            {str(p[PHASE_FIELDS.name])}
                          </span>
                        ) : null}
                        {p[PHASE_FIELDS.durationWeeks] != null ? (
                          <Pill tone="neutral">
                            {str(p[PHASE_FIELDS.durationWeeks])}{" "}
                            {UI_LABELS.weekSuffix}
                          </Pill>
                        ) : null}
                        {p[PHASE_FIELDS.percentageOfTotal] != null ? (
                          <span className="text-[11px] text-zinc-500">
                            {str(p[PHASE_FIELDS.percentageOfTotal])}{" "}
                            {UI_LABELS.phaseTimelineSuffix}
                          </span>
                        ) : null}
                      </summary>
                      <div className="border-t border-zinc-800/50 px-3 pb-3 pt-2">
                        {milestones.length > 0 ? (
                          <div className="mb-3">
                            <p className="text-[11px] font-medium uppercase text-zinc-500">
                              {UI_LABELS.milestones}
                            </p>
                            <ul className="mt-1 list-disc pl-4 text-xs text-zinc-400">
                              {milestones.map((m, mi) => (
                                <li key={mi}>{str(m)}</li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {tasks.length === 0 ? (
                          <p className="text-xs text-zinc-500">
                            {UI_LABELS.emptyPhaseTasks}
                          </p>
                        ) : (
                          <div className="-mx-3 overflow-x-auto">
                            <table className="w-full min-w-[560px] border-collapse">
                              <thead>
                                <tr>
                                  {TASK_TABLE.headers.map((h) => (
                                    <Th
                                      key={h}
                                      className={
                                        h === "Hrs" ? "whitespace-nowrap" : ""
                                      }
                                    >
                                      {h}
                                    </Th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {tasks.map((t, ti) => {
                                  const tk =
                                    t &&
                                    typeof t === "object" &&
                                    !Array.isArray(t)
                                      ? (t as Record<string, unknown>)
                                      : {}
                                  const flags: string[] = []
                                  if (tk[TASK_TABLE.flagCritical] === true)
                                    flags.push("critical")
                                  if (tk[TASK_TABLE.flagRisk] === true)
                                    flags.push("risk")
                                  return (
                                    <tr key={str(tk.id) || ti}>
                                      <Td className="font-mono text-[11px] text-zinc-500">
                                        {tk.id != null ? str(tk.id) : "—"}
                                      </Td>
                                      <Td className="max-w-[220px]">
                                        {tk.name != null ? str(tk.name) : "—"}
                                      </Td>
                                      <Td className="whitespace-nowrap text-zinc-400">
                                        {tk.owner_role != null
                                          ? str(tk.owner_role)
                                          : "—"}
                                      </Td>
                                      <Td>
                                        {tk.effort_hours != null
                                          ? str(tk.effort_hours)
                                          : "—"}
                                      </Td>
                                      <Td>
                                        <div className="flex flex-wrap gap-1">
                                          {flags.map((f) => (
                                            <Pill
                                              key={f}
                                              tone={
                                                f === "risk" ? "amber" : "blue"
                                              }
                                            >
                                              {f}
                                            </Pill>
                                          ))}
                                          {flags.length === 0 ? (
                                            <span className="text-zinc-600">
                                              —
                                            </span>
                                          ) : null}
                                        </div>
                                      </Td>
                                    </tr>
                                  )
                                })}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    </details>
                  )
                })
              )}
            </div>
          </>
        )}
      </Section>

      <Section id={PLAN_SECTIONS.risks.id} title={PLAN_SECTIONS.risks.title}>
        {riskRegister.length === 0 ? (
          <p className="text-sm text-zinc-500">{UI_LABELS.emptyRisks}</p>
        ) : (
          <div className="-mx-4 overflow-x-auto sm:mx-0">
            <table className="w-full min-w-[720px] border-collapse">
              <thead>
                <tr>
                  {RISK_TABLE.headers.map((h) => (
                    <Th key={h}>{h}</Th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {riskRegister.map((row, i) => {
                  const o =
                    row && typeof row === "object" && !Array.isArray(row)
                      ? (row as Record<string, unknown>)
                      : {}
                  const f = RISK_TABLE.fields
                  const pi = [
                    o[f.probability],
                    o[f.impact],
                  ]
                    .filter((x) => x != null)
                    .map((x) => str(x))
                    .join(" / ")
                  return (
                    <tr key={str(o[f.id]) || i}>
                      <Td className="font-mono text-[11px]">
                        {str(o[f.id] ?? "—")}
                      </Td>
                      <Td className="whitespace-nowrap">
                        {str(o[f.category] ?? "—")}
                      </Td>
                      <Td className="max-w-[240px]">
                        {str(o[f.description] ?? "—")}
                      </Td>
                      <Td className="whitespace-nowrap text-[11px]">
                        {pi || str(o[f.score] ?? "—")}
                      </Td>
                      <Td className="max-w-[200px] text-zinc-400">
                        {str(o[f.mitigation] ?? "—")}
                      </Td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section
        id={PLAN_SECTIONS.staffing.id}
        title={PLAN_SECTIONS.staffing.title}
      >
        {staffing.length === 0 ? (
          <p className="text-sm text-zinc-500">{UI_LABELS.emptyStaffing}</p>
        ) : (
          <div className="-mx-4 overflow-x-auto sm:mx-0">
            <table className="w-full min-w-[640px] border-collapse">
              <thead>
                <tr>
                  {STAFFING_TABLE.headers.map((h) => (
                    <Th
                      key={h}
                      className={
                        h === "Hours" || h === "Alloc %"
                          ? "whitespace-nowrap"
                          : ""
                      }
                    >
                      {h}
                    </Th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {staffing.map((row, i) => {
                  const o =
                    row && typeof row === "object" && !Array.isArray(row)
                      ? (row as Record<string, unknown>)
                      : {}
                  const sf = STAFFING_TABLE.fields
                  const phasesInv = Array.isArray(o[sf.phaseInvolvement])
                    ? (o[sf.phaseInvolvement] as unknown[])
                        .map((x) => str(x))
                        .join(", ")
                    : "—"
                  const skills = Array.isArray(o[sf.skillsRequired])
                    ? (o[sf.skillsRequired] as unknown[])
                        .map((x) => str(x))
                        .join(", ")
                    : "—"
                  return (
                    <tr key={str(o[sf.role]) || i}>
                      <Td className="font-medium text-zinc-200">
                        {str(o[sf.role] ?? "—")}
                        {o[sf.criticalPath] === true ? (
                          <span className="ml-2 mt-1 block">
                            <Pill tone="blue">
                              {UI_LABELS.criticalPathBadge}
                            </Pill>
                          </span>
                        ) : null}
                      </Td>
                      <Td className="font-mono text-[11px] text-zinc-400">
                        {phasesInv}
                      </Td>
                      <Td>
                        {o[sf.totalHours] != null
                          ? str(o[sf.totalHours])
                          : "—"}
                      </Td>
                      <Td>
                        {o[sf.allocationPercent] != null
                          ? `${str(o[sf.allocationPercent])}%`
                          : "—"}
                      </Td>
                      <Td className="max-w-[200px] text-zinc-400">{skills}</Td>
                      <Td className="max-w-[180px] text-zinc-500">
                        {str(o[sf.notes] ?? "—")}
                      </Td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {openQs.length > 0 ? (
        <Section
          id={PLAN_SECTIONS.openQuestions.id}
          title={PLAN_SECTIONS.openQuestions.title}
        >
          <ol className="list-decimal space-y-3 pl-5 text-sm text-zinc-300">
            {openQs.map((q, i) => {
              const o =
                q && typeof q === "object" && !Array.isArray(q)
                  ? (q as Record<string, unknown>)
                  : {}
              const fq = OPEN_QUESTION_FIELDS
              return (
                <li key={i}>
                  <p>{str(o[fq.question] ?? o)}</p>
                  <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-zinc-500">
                    {o[fq.urgency] != null ? (
                      <span>Urgency: {str(o[fq.urgency])}</span>
                    ) : null}
                    {o[fq.impactIfUnanswered] != null ? (
                      <span>
                        Impact: {str(o[fq.impactIfUnanswered])}
                      </span>
                    ) : null}
                  </div>
                </li>
              )
            })}
          </ol>
        </Section>
      ) : null}

      {viability &&
      Object.keys(viability).some((k) => viability[k] != null) ? (
        <Section
          id={PLAN_SECTIONS.viability.id}
          title={PLAN_SECTIONS.viability.title}
        >
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border border-zinc-800/60 bg-zinc-900/40 p-3 text-[11px] text-zinc-400">
            {JSON.stringify(viability, null, 2)}
          </pre>
        </Section>
      ) : null}
    </div>
  )
}
