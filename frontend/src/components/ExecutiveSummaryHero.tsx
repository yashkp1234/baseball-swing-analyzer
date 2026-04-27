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
  const primaryWhy = summary.nextSteps[0]?.why;
  const terms = summary.terms ?? [];

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
              {primaryWhy ? <p className="mt-2 text-sm leading-6 text-[var(--color-text-dim)]">{primaryWhy}</p> : null}
            </div>
          ) : null}

          {terms.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-dim)]">
                Plain-English terms
              </p>
              <dl className="grid gap-3 sm:grid-cols-2">
                {terms.map((item) => (
                  <div key={item.term} className="border-l border-[var(--color-accent)]/35 pl-3">
                    <dt className="text-sm font-medium text-[var(--color-text)]">{item.term}</dt>
                    <dd className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">{item.definition}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
