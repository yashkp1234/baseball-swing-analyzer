import { useState } from "react";
import { LoaderCircle, RotateCcw } from "lucide-react";
import type { ProjectionSummary, SportProfile } from "@/lib/api";

export interface ProjectionInput {
  x_factor_delta_deg: number;
  head_stability_delta_norm: number;
}

interface SliderRowProps {
  label: string;
  description: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (value: number) => void;
  onCommit: () => void;
}

function SliderRow({ label, description, value, min, max, step, unit, onChange, onCommit }: SliderRowProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-[var(--color-text-dim)]" style={{ fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}>
            {label}
          </p>
          <p className="mt-1 text-[11px] leading-snug text-[var(--color-text-dim)]">{description}</p>
        </div>
        <div className="flex items-center gap-1 rounded-md bg-[var(--color-surface-2)] px-2 py-1 text-right">
          <input
            type="number"
            value={value}
            min={min}
            max={max}
            step={step}
            onChange={(event) => onChange(Number(event.target.value))}
            onBlur={onCommit}
            onKeyUp={(event) => {
              if (event.key === "Enter") onCommit();
            }}
            className="w-20 bg-transparent text-right text-sm font-semibold text-[var(--color-text)] outline-none"
            style={{ fontFamily: "DM Mono, monospace" }}
          />
          {unit ? <span className="text-xs text-[var(--color-text-dim)]">{unit}</span> : null}
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        onMouseUp={onCommit}
        onTouchEnd={onCommit}
        className="w-full accent-[var(--color-accent)]"
      />
    </div>
  );
}

interface Props {
  baselineXFactor: number;
  baselineHeadDisplacementPx: number;
  sportProfile: SportProfile | null;
  baseline: ProjectionSummary | null;
  projection: ProjectionSummary | null;
  pending: boolean;
  error: string | null;
  onApply: (input: ProjectionInput) => void;
  onReset: () => void;
}

function formatRange(low: number, high: number, unit: string): string {
  return `${low.toFixed(0)}-${high.toFixed(0)} ${unit}`;
}

export function WhatIfSimulator({
  baselineXFactor,
  baselineHeadDisplacementPx,
  sportProfile,
  baseline,
  projection,
  pending,
  error,
  onApply,
  onReset,
}: Props) {
  const [draft, setDraft] = useState<ProjectionInput>({ x_factor_delta_deg: 0, head_stability_delta_norm: 0 });

  const commit = () => onApply(draft);
  const activeProjection = projection ?? baseline;

  return (
    <div className="flex h-full flex-col gap-5">
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3">
          <p className="text-[10px] uppercase tracking-widest text-[var(--color-text-dim)]" style={{ fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}>
            Estimated EV
          </p>
          <p className="mt-2 text-2xl font-bold text-[var(--color-text)]" style={{ fontFamily: "DM Mono, monospace" }}>
            {baseline ? formatRange(baseline.exit_velocity_mph_low, baseline.exit_velocity_mph_high, "mph") : "-"}
          </p>
        </div>
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3">
          <p className="text-[10px] uppercase tracking-widest text-[var(--color-text-dim)]" style={{ fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}>
            Projected EV
          </p>
          <p className="mt-2 text-2xl font-bold text-[var(--color-accent)]" style={{ fontFamily: "DM Mono, monospace" }}>
            {activeProjection ? formatRange(activeProjection.exit_velocity_mph_low, activeProjection.exit_velocity_mph_high, "mph") : "-"}
          </p>
        </div>
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3">
          <p className="text-[10px] uppercase tracking-widest text-[var(--color-text-dim)]" style={{ fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}>
            Estimated Carry
          </p>
          <p className="mt-2 text-2xl font-bold text-[var(--color-text)]" style={{ fontFamily: "DM Mono, monospace" }}>
            {activeProjection ? formatRange(activeProjection.carry_distance_ft_low, activeProjection.carry_distance_ft_high, "ft") : "-"}
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-[11px] text-[var(--color-text-dim)]">
        Pose-only projection using body mechanics proxies. These are directional estimate ranges, not measured ball-flight outcomes.
        {sportProfile?.label === "unknown" ? " Using shared hitting calibration because sport was not confidently detected." : ""}
        <span className="ml-2 font-mono text-[var(--color-text)]">
          Score {baseline ? baseline.score : "-"}{projection ? ` -> ${projection.score}` : ""}
        </span>
      </div>

      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3 text-xs text-[var(--color-text-dim)]">
        Baseline mechanics: <span className="font-mono text-[var(--color-text)]">{baselineXFactor.toFixed(1)} deg X-factor</span> and{" "}
        <span className="font-mono text-[var(--color-text)]">{baselineHeadDisplacementPx.toFixed(1)} px head drift</span>.
      </div>

      <div className="space-y-5">
        <SliderRow
          label="Add Separation"
          description="Positive values rotate the shoulder chain farther behind the hips into contact."
          value={draft.x_factor_delta_deg}
          min={-12}
          max={12}
          step={1}
          unit="deg"
          onChange={(value) => setDraft((current) => ({ ...current, x_factor_delta_deg: value }))}
          onCommit={commit}
        />

        <SliderRow
          label="Stabilize Head"
          description="Positive values reduce upper-body drift in the normalized 3D viewer space."
          value={draft.head_stability_delta_norm}
          min={-0.12}
          max={0.12}
          step={0.01}
          unit=""
          onChange={(value) => setDraft((current) => ({ ...current, head_stability_delta_norm: value }))}
          onCommit={commit}
        />
      </div>

      <div className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-xs text-[var(--color-text-dim)]">
        <div className="flex items-center gap-2">
          {pending ? <LoaderCircle className="h-4 w-4 animate-spin text-[var(--color-accent)]" /> : null}
          <span>{pending ? "Updating projected swing..." : "Apply a change by releasing a slider."}</span>
        </div>
        <button
          type="button"
          onClick={onReset}
          className="inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] px-2 py-1 text-[var(--color-text)] hover:border-[var(--color-accent)]"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Reset
        </button>
      </div>

      {error ? <p className="text-xs text-[var(--color-red)]">{error}</p> : null}
      {activeProjection?.notes?.length ? (
        <ul className="space-y-1 text-xs text-[var(--color-text-dim)]">
          {activeProjection.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
