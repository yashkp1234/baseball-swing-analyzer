import { useEffect, useMemo, useState } from "react";
import type { SwingMetrics } from "@/lib/api";
import { computeScore, scoreLabel } from "@/lib/scoring";

interface Props {
  metrics: Partial<SwingMetrics>;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function formatDelta(delta: number): string {
  if (delta > 0) return `+${delta}`;
  if (delta < 0) return `${delta}`;
  return "0";
}

function SliderTrack({
  min,
  max,
  goodStart,
  goodEnd,
}: {
  min: number;
  max: number;
  goodStart: number;
  goodEnd: number;
}) {
  const start = ((goodStart - min) / (max - min)) * 100;
  const width = ((goodEnd - goodStart) / (max - min)) * 100;
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-[var(--color-surface-2)]"
    >
      <div
        className="absolute h-full rounded-full bg-[var(--color-accent)]/30"
        style={{ left: `${start}%`, width: `${width}%` }}
      />
    </div>
  );
}

function SliderRow({
  label,
  description,
  value,
  min,
  max,
  step,
  unit,
  goodStart,
  goodEnd,
  onChange,
}: {
  label: string;
  description: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  goodStart: number;
  goodEnd: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-[var(--color-text)]">{label}</p>
          <p className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">{description}</p>
        </div>
        <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1.5 text-sm font-semibold text-[var(--color-text)]">
          {Math.round(value)}{unit}
        </div>
      </div>
      <div className="relative">
        <SliderTrack min={min} max={max} goodStart={goodStart} goodEnd={goodEnd} />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          className="relative z-10 w-full accent-[var(--color-accent)]"
          aria-label={label}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-[var(--color-text-dim)]">
        <span>{min}{unit}</span>
        <span>Best zone {goodStart}-{goodEnd}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  );
}

export function WhatIfSimulator({ metrics }: Props) {
  const baselineXFactor = typeof metrics.x_factor_at_contact === "number" ? metrics.x_factor_at_contact : 0;
  const baselineHeadMovement =
    typeof metrics.head_displacement_total === "number" ? metrics.head_displacement_total : 0;

  const [xFactor, setXFactor] = useState(baselineXFactor);
  const [headMovement, setHeadMovement] = useState(baselineHeadMovement);

  useEffect(() => {
    setXFactor(baselineXFactor);
    setHeadMovement(baselineHeadMovement);
  }, [baselineHeadMovement, baselineXFactor]);

  const baselineScore = useMemo(() => computeScore(metrics), [metrics]);
  const projectedScore = useMemo(
    () =>
      computeScore(metrics, {
        x_factor_at_contact: xFactor,
        head_displacement_total: headMovement,
      }),
    [headMovement, metrics, xFactor],
  );
  const delta = projectedScore - baselineScore;
  const projectedBand = scoreLabel(projectedScore);

  return (
    <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[var(--color-text)]">What happens if you clean this up?</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--color-text-dim)]">
            Move the two biggest levers and watch the swing score update instantly. This stays client-side and does not rerun the backend analysis.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-[var(--color-surface-2)] px-4 py-3">
            <p className="text-xs text-[var(--color-text-dim)]">Current score</p>
            <p className="mt-1 text-3xl font-semibold text-[var(--color-text)]">{baselineScore}</p>
          </div>
          <div className="rounded-lg bg-[var(--color-surface-2)] px-4 py-3">
            <p className="text-xs text-[var(--color-text-dim)]">Projected score</p>
            <p className="mt-1 text-3xl font-semibold" style={{ color: projectedBand.color }}>{projectedScore}</p>
          </div>
        </div>
      </div>

      <p className="mt-4 text-sm font-medium" style={{ color: delta >= 0 ? "var(--color-accent)" : "var(--color-amber)" }}>
        If you reach both targets, your score goes from {baselineScore} to {projectedScore} ({formatDelta(delta)} points).
      </p>

      <div className="mt-5 space-y-6">
        <SliderRow
          label="Hip-Shoulder Separation"
          description="This is the gap between how far the hips and shoulders have turned at contact."
          value={xFactor}
          min={-20}
          max={60}
          step={1}
          unit="°"
          goodStart={20}
          goodEnd={45}
          onChange={(value) => setXFactor(clamp(value, -20, 60))}
        />

        <SliderRow
          label="Head Stability"
          description="Lower head movement usually means the body stays more centered from load to contact."
          value={headMovement}
          min={0}
          max={100}
          step={1}
          unit="px"
          goodStart={0}
          goodEnd={30}
          onChange={(value) => setHeadMovement(clamp(value, 0, 100))}
        />
      </div>
    </section>
  );
}
