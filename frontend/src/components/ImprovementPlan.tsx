import { ArrowRight, CheckCircle2, CircleAlert, Info } from "lucide-react";
import { Card, CardTitle } from "@/components/Card";
import { FlagBadge } from "@/components/FlagsPanel";
import type { CoachingLine, SwingMetrics } from "@/lib/api";

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
  nextSteps: string[];
  coaching: CoachingLine[];
  flags: SwingMetrics["flags"];
}

function toneForStep(step: string, coaching: CoachingLine[]): CoachingLine["tone"] {
  return coaching.find((line) => line.text.trim() === step.trim())?.tone ?? "info";
}

export function ImprovementPlan({ nextSteps, coaching, flags }: ImprovementPlanProps) {
  return (
    <Card className="rounded-[24px] p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl">
          <CardTitle className="mb-2 px-0">What to improve next</CardTitle>
          <p className="text-sm leading-6 text-[var(--color-text-dim)]">
            Keep the next block tight: reinforce the move quality that is already present, then attack the biggest
            leak showing up in the summary and flags.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <FlagBadge
            label="Shoulder"
            value={flags.front_shoulder_closed_load}
            type={flags.front_shoulder_closed_load ? "good" : "warn"}
          />
          <FlagBadge label="Finish" value={flags.finish_height} type={flags.finish_height === "high" ? "good" : "warn"} />
          <FlagBadge label="Hip casting" value={flags.hip_casting} type={flags.hip_casting ? "warn" : "good"} />
        </div>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        {nextSteps.map((step, index) => {
          const tone = toneForStep(step, coaching);
          const Icon = TONE_ICON[tone];

          return (
            <div key={`${index}-${step}`} className="rounded-[20px] border border-[var(--color-border)] bg-[var(--color-surface-2)]/50 p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--color-text-dim)]">
                  Step {index + 1}
                </span>
                <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium ${TONE_CLASS[tone]}`}>
                  <Icon className="h-3.5 w-3.5" />
                  {tone === "good" ? "Reinforce" : tone === "warn" ? "Correct" : "Review"}
                </span>
              </div>
              <p className="mt-3 text-sm leading-6 text-[var(--color-text)]">{step}</p>
              <div className="mt-4 flex items-center gap-2 text-xs text-[var(--color-text-dim)]">
                <ArrowRight className="h-3.5 w-3.5" />
                One clear cue at a time.
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
