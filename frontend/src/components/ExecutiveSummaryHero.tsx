import type { ExecutiveSummaryModel } from "@/lib/resultsSummary";

interface ExecutiveSummaryHeroProps {
  summary: ExecutiveSummaryModel;
  embedded?: boolean;
}

function scoreAccent(score: number): string {
  if (score >= 85) return "text-[var(--color-accent)]";
  if (score >= 70) return "text-[var(--color-amber)]";
  return "text-[var(--color-red)]";
}

export function ExecutiveSummaryHero({ summary, embedded = false }: ExecutiveSummaryHeroProps) {
  const primaryStep = summary.nextSteps[0]?.text;
  const supportingSteps = summary.nextSteps.slice(1, 3);

  return (
    <section
      className={
        embedded
          ? "h-full"
          : "rounded-2xl border border-white/10 bg-[var(--color-surface)] p-6 shadow-[0_18px_60px_rgba(0,0,0,0.24)]"
      }
    >
      <div className={embedded ? "grid h-full gap-6 px-6 py-6 lg:grid-cols-[180px_minmax(0,1fr)] lg:items-center lg:px-8 lg:py-8" : "grid gap-5 lg:grid-cols-[180px_minmax(0,1fr)] lg:items-center"}>
        <div>
          <p className={`text-6xl font-semibold leading-none lg:text-7xl ${scoreAccent(summary.score)}`}>
            {summary.score}
          </p>
          <p className="mt-2 text-xl font-semibold text-[var(--color-text)]">{summary.label}</p>
        </div>

        <div className="space-y-4">
          <p className="max-w-3xl text-base leading-7 text-[var(--color-text)]">
            {summary.summary}
          </p>

          {primaryStep ? (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-dim)]">
                Work on this first
              </p>
              <p className="mt-2 text-sm leading-6 text-[var(--color-text)]">{primaryStep}</p>
            </div>
          ) : null}

          {supportingSteps.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {supportingSteps.map((step) => (
                <p key={step.text} className="rounded-lg border border-white/8 bg-white/4 px-3 py-2 text-sm leading-6 text-[var(--color-text-dim)]">
                  {step.text}
                </p>
              ))}
            </div>
          ) : null}
          </div>
      </div>
    </section>
  );
}
