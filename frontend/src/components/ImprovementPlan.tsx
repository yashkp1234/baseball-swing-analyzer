import { CheckCircle2, CircleAlert, Info } from "lucide-react";
import { Card, CardTitle } from "@/components/Card";
import { FlagBadge } from "@/components/FlagsPanel";
import type { CoachingLine, SwingMetrics } from "@/lib/api";
import type { ExecutiveSummaryStep } from "@/lib/resultsSummary";

const TONE_ICON = {
  good: CheckCircle2,
  warn: CircleAlert,
  info: Info,
} satisfies Record<CoachingLine["tone"], typeof CheckCircle2>;

const TONE_CLASS = {
  good: "border-[var(--color-accent)]/25 bg-[var(--color-accent)]/8 text-[var(--color-accent)]",
  warn: "border-[var(--color-amber)]/25 bg-[var(--color-amber)]/8 text-[var(--color-amber)]",
  info: "border-[var(--color-border)] bg-[var(--color-surface-2)]/80 text-[var(--color-text-dim)]",
} satisfies Record<CoachingLine["tone"], string>;

interface ImprovementPlanProps {
  nextSteps: ExecutiveSummaryStep[];
  flags: SwingMetrics["flags"];
}

export function ImprovementPlan({ nextSteps, flags }: ImprovementPlanProps) {
  return (
    <Card className="rounded-[24px] p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl">
          <CardTitle className="mb-2 px-0">What to improve next</CardTitle>
          <p className="text-sm leading-6 text-[var(--color-text-dim)]">
            Treat these as your next coaching cues. Start with the first one and ignore the rest until that move feels
            more repeatable.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <FlagBadge
            label="Front shoulder"
            value={flags.front_shoulder_closed_load}
            type={flags.front_shoulder_closed_load ? "good" : "warn"}
          />
          <FlagBadge label="Finish height" value={flags.finish_height} type={flags.finish_height === "high" ? "good" : "warn"} />
          <FlagBadge label="Hips spinning early" value={flags.hip_casting} type={flags.hip_casting ? "warn" : "good"} />
        </div>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        {nextSteps.map((step, index) => {
          const tone = step.tone;
          const Icon = TONE_ICON[tone];

          return (
            <div
              key={`${index}-${step.text}`}
              className="rounded-[20px] border border-[var(--color-border)] bg-[var(--color-surface-2)]/50 p-4"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--color-text-dim)]">
                  Step {index + 1}
                </span>
                <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium ${TONE_CLASS[tone]}`}>
                  <Icon className="h-3.5 w-3.5" />
                  {tone === "good" ? "Reinforce" : tone === "warn" ? "Correct" : "Review"}
                </span>
              </div>
              <p className="mt-3 text-sm leading-6 text-[var(--color-text)]">{step.text}</p>
              {step.why ? <p className="mt-4 text-xs leading-5 text-[var(--color-text-dim)]">{step.why}</p> : null}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
