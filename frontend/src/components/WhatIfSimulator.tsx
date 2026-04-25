import { useState } from "react";
import { computeScore, scoreLabel } from "@/lib/scoring";
import { METRIC_RANGES } from "@/lib/metrics";
import type { SwingMetrics } from "@/lib/api";

interface SliderRowProps {
  label: string;
  unit: string;
  value: number;
  min: number;
  max: number;
  goodMin: number;
  goodMax: number;
  onChange: (v: number) => void;
}

function SliderRow({ label, unit, value, min, max, goodMin, goodMax, onChange }: SliderRowProps) {
  const range = max - min;
  const goodLeftPct = ((goodMin - min) / range) * 100;
  const goodWidthPct = ((goodMax - goodMin) / range) * 100;
  const inGood = value >= goodMin && value <= goodMax;

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-baseline">
        <span
          className="text-xs uppercase tracking-widest"
          style={{ color: "var(--color-text-dim)", fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}
        >
          {label}
        </span>
        <div className="flex items-baseline gap-1">
          <span
            className="text-xl font-bold"
            style={{ color: inGood ? "var(--color-accent)" : "var(--color-red)", fontFamily: "DM Mono, monospace" }}
          >
            {value.toFixed(0)}{unit}
          </span>
          <span className="text-[10px] text-[var(--color-text-dim)]" style={{ fontFamily: "DM Mono, monospace" }}>
            [{goodMin}–{goodMax}{unit}]
          </span>
        </div>
      </div>

      <div className="relative h-5 flex items-center">
        {/* Base track */}
        <div className="absolute inset-x-0 h-1.5 rounded-full bg-[var(--color-surface-2)]" />
        {/* Good-zone highlight */}
        <div
          className="absolute h-1.5 rounded-full"
          style={{
            left: `${goodLeftPct}%`,
            width: `${goodWidthPct}%`,
            background: "linear-gradient(90deg, rgba(0,255,135,0.15), rgba(0,255,135,0.35), rgba(0,255,135,0.15))",
            border: "1px solid rgba(0,255,135,0.2)",
          }}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={1}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label={label}
          className="relative w-full h-1.5 appearance-none bg-transparent cursor-pointer"
        />
      </div>
    </div>
  );
}

interface Props {
  metrics: SwingMetrics;
}

export function WhatIfSimulator({ metrics }: Props) {
  const xRange = METRIC_RANGES.x_factor_at_contact!;
  const headRange = METRIC_RANGES.head_displacement_total!;

  const [xFactor, setXFactor] = useState(Math.round(metrics.x_factor_at_contact ?? 0));
  const [headMove, setHeadMove] = useState(Math.round(metrics.head_displacement_total ?? 40));

  const currentScore = computeScore(metrics);
  const projectedScore = computeScore(metrics, {
    x_factor_at_contact: xFactor,
    head_displacement_total: headMove,
  });

  const diff = projectedScore - currentScore;
  const { label: currentLabel } = scoreLabel(currentScore);
  const { label: projLabel, color: projColor } = scoreLabel(projectedScore);

  return (
    <div className="space-y-6">
      {/* Score comparison */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <div className="text-center p-4 rounded-lg bg-[var(--color-surface-2)] border border-[var(--color-border)]">
          <p className="text-[10px] uppercase tracking-widest text-[var(--color-text-dim)] mb-1" style={{ fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}>Current</p>
          <p className="text-4xl font-bold text-[var(--color-text)]" style={{ fontFamily: "DM Mono, monospace" }}>{currentScore}</p>
          <p className="text-xs text-[var(--color-text-dim)] mt-0.5">{currentLabel}</p>
        </div>

        <div className="flex flex-col items-center gap-1">
          <div className="h-px w-full bg-[var(--color-border)]" />
          {diff !== 0 && (
            <p
              className="text-base font-bold"
              style={{
                color: diff > 0 ? "var(--color-accent)" : "var(--color-red)",
                fontFamily: "DM Mono, monospace",
              }}
            >
              {diff > 0 ? `+${diff}` : diff}
            </p>
          )}
          {diff === 0 && (
            <p className="text-xs text-[var(--color-text-dim)]" style={{ fontFamily: "DM Mono, monospace" }}>—</p>
          )}
        </div>

        <div
          className="text-center p-4 rounded-lg border"
          style={{
            background: `color-mix(in srgb, ${projColor}10, var(--color-surface-2))`,
            borderColor: `${projColor}33`,
          }}
        >
          <p className="text-[10px] uppercase tracking-widest text-[var(--color-text-dim)] mb-1" style={{ fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}>Projected</p>
          <p className="text-4xl font-bold" style={{ color: projColor, fontFamily: "DM Mono, monospace" }}>{projectedScore}</p>
          <p className="text-xs mt-0.5" style={{ color: projColor }}>{projLabel}</p>
        </div>
      </div>

      {/* Sliders */}
      <div className="space-y-5">
        <SliderRow
          label="Hip–Shoulder Separation (X-Factor)"
          unit="°"
          value={xFactor}
          min={-20}
          max={60}
          goodMin={xRange.good[0]}
          goodMax={xRange.good[1]}
          onChange={setXFactor}
        />
        <SliderRow
          label="Head Stability"
          unit="px"
          value={headMove}
          min={0}
          max={120}
          goodMin={headRange.good[0]}
          goodMax={headRange.good[1]}
          onChange={setHeadMove}
        />
      </div>

      <p className="text-xs text-[var(--color-text-dim)] leading-relaxed border-t border-[var(--color-border)] pt-3">
        Green zone = target range. Drag to see how fixing mechanics changes your score.
      </p>
    </div>
  );
}
