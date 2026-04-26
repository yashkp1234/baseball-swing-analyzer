import { LoaderCircle } from "lucide-react";
import type { ProjectionResponse, ProjectionSummary } from "@/lib/api";

interface Props {
  enabled: boolean;
  pending: boolean;
  baseline: ProjectionSummary | null;
  projection: ProjectionSummary | null;
  fix: ProjectionResponse["fix"] | null | undefined;
  error?: string | null;
  onToggle: (enabled: boolean) => void;
}

function estimate(summary: ProjectionSummary | null, key: "score" | "exit_velocity_mph" | "carry_distance_ft"): string {
  if (!summary) return "-";
  return String(Math.round(Number(summary[key])));
}

export function FixTogglePanel({ enabled, pending, baseline, projection, fix, error, onToggle }: Props) {
  const active = enabled && projection ? projection : baseline;
  const inactive = enabled ? baseline : projection;

  return (
    <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-[var(--color-text)]">
            {fix?.label ?? "Fix lower-half timing"}
          </h2>
          <p className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">
            {fix?.coach_text ?? "Keep the stride controlled so the front side braces before the swing turns."}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          onClick={() => onToggle(!enabled)}
          className="inline-flex min-w-24 items-center justify-center rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm font-semibold text-[var(--color-text)] hover:border-[var(--color-accent)]"
        >
          {pending ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : null}
          {enabled ? "Fix on" : "Fix off"}
        </button>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-[var(--color-surface-2)] p-3">
          <p className="text-xs text-[var(--color-text-dim)]">Score</p>
          <p className="mt-1 text-2xl font-semibold text-[var(--color-text)]">{estimate(active, "score")}</p>
          {inactive ? <p className="mt-1 text-xs text-[var(--color-text-dim)]">was {estimate(inactive, "score")}</p> : null}
        </div>
        <div className="rounded-lg bg-[var(--color-surface-2)] p-3">
          <p className="text-xs text-[var(--color-text-dim)]">Est. EV</p>
          <p className="mt-1 text-2xl font-semibold text-[var(--color-text)]">{estimate(active, "exit_velocity_mph")} mph</p>
          {inactive ? <p className="mt-1 text-xs text-[var(--color-text-dim)]">was {estimate(inactive, "exit_velocity_mph")} mph</p> : null}
        </div>
        <div className="rounded-lg bg-[var(--color-surface-2)] p-3">
          <p className="text-xs text-[var(--color-text-dim)]">Est. Carry</p>
          <p className="mt-1 text-2xl font-semibold text-[var(--color-text)]">{estimate(active, "carry_distance_ft")} ft</p>
          {inactive ? <p className="mt-1 text-xs text-[var(--color-text-dim)]">was {estimate(inactive, "carry_distance_ft")} ft</p> : null}
        </div>
      </div>

      <p className="mt-3 text-xs leading-5 text-[var(--color-text-dim)]">
        Estimates are based on pose mechanics, not measured ball flight.
      </p>
      {error ? <p className="mt-2 text-xs text-[var(--color-red)]">{error}</p> : null}
    </section>
  );
}
