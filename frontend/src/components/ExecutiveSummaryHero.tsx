import { Activity, Medal, Radar } from "lucide-react";
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
  return (
    <section
      className={
        embedded
          ? "h-full"
          : "overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,rgba(13,18,28,0.98),rgba(22,28,38,0.94))] shadow-[0_24px_80px_rgba(0,0,0,0.28)]"
      }
    >
      <div className="border-b border-white/8 px-6 py-4 lg:px-8">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/4 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
          <Radar className="h-3.5 w-3.5" />
          Executive Summary
        </div>
      </div>

      <div className="grid gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)] lg:px-8 lg:py-8">
        <div className="space-y-5">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <p className={`text-6xl font-semibold leading-none lg:text-7xl ${scoreAccent(summary.score)}`}>
                {summary.score}
              </p>
              <p className="mt-3 text-lg font-semibold text-[var(--color-text)] lg:text-2xl">
                {summary.label}
              </p>
            </div>
            <div className="max-w-xs rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-[var(--color-text-dim)]">
                <Medal className="h-3.5 w-3.5" />
                Score Signal
              </div>
              <p className="mt-2 text-sm leading-6 text-[var(--color-text)]">
                Built from rotation, posture, lower-half leverage, stability, and hand-speed signals already returned by the analysis API.
              </p>
            </div>
          </div>

          <p className="max-w-3xl text-sm leading-7 text-[var(--color-text-dim)] lg:text-base">
            {summary.summary}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-[var(--color-text-dim)]">
              <Activity className="h-3.5 w-3.5" />
              Evidence Layer
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--color-text)]">
              The annotated video below is the proof surface for this summary, so the report stays tied to the actual move.
            </p>
          </div>
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--color-text-dim)]">
              Immediate Read
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--color-text)]">
              Start with the score and one-line verdict, then verify it against the swing before digging into the deeper diagnostics.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
