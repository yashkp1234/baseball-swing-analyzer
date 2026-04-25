import { useMemo } from "react";
import type { Frame3D, EnergyLossEvent } from "@/lib/api";
import { PHASE_COLORS } from "@/lib/metrics";

const PHASE_LABELS: Record<string, string> = {
  idle: "Idle",
  stance: "Stance",
  load: "Load",
  stride: "Stride",
  swing: "Launch",
  contact: "Contact",
  follow_through: "Follow",
};

interface PhaseGroup {
  phase: string;
  label: string;
  avgVelocity: number;
  frameCount: number;
  hasLeak: boolean;
}

function phaseInsight(group: PhaseGroup, allGroups: PhaseGroup[]): string {
  const idx = allGroups.indexOf(group);
  const prev = allGroups[idx - 1];

  if (group.hasLeak) return "Power leaked here — add drills targeting this phase.";
  if (group.phase === "contact") {
    return group.avgVelocity > 0
      ? "Peak power at contact — that's the goal."
      : "Contact is instantaneous — hard to measure velocity here.";
  }
  if (prev && group.avgVelocity > prev.avgVelocity * 1.1)
    return "Good — power building through this phase.";
  if (prev && group.avgVelocity < prev.avgVelocity * 0.85)
    return "Speed dropped — check your mechanics here.";
  return "Holding steady through this phase.";
}

interface Props {
  frames: Frame3D[];
  phaseLabels: string[];
  energyLossEvents: EnergyLossEvent[];
}

export function PhaseEnergyChart({ frames, phaseLabels, energyLossEvents }: Props) {
  const leakFrames = useMemo(
    () => new Set(energyLossEvents.filter((e) => e.magnitude_pct > 30).map((e) => e.frame)),
    [energyLossEvents]
  );

  const groups = useMemo<PhaseGroup[]>(() => {
    const map = new Map<string, { total: number; count: number; hasLeak: boolean }>();
    const order: string[] = [];
    phaseLabels.forEach((phase, i) => {
      if (!map.has(phase)) { map.set(phase, { total: 0, count: 0, hasLeak: false }); order.push(phase); }
      const entry = map.get(phase)!;
      const vel = frames[i]?.velocities?.right_wrist ?? frames[i]?.velocities?.left_wrist ?? 0;
      entry.total += vel;
      entry.count += 1;
      if (leakFrames.has(i)) entry.hasLeak = true;
    });
    return order
      .filter((p) => p !== "idle")
      .map((phase) => {
        const { total, count, hasLeak } = map.get(phase)!;
        return { phase, label: PHASE_LABELS[phase] ?? phase, avgVelocity: count ? total / count : 0, frameCount: count, hasLeak };
      });
  }, [frames, phaseLabels, leakFrames]);

  const maxVel = useMemo(() => Math.max(...groups.map((g) => g.avgVelocity), 1), [groups]);

  if (groups.length === 0) {
    return <p className="text-sm text-[var(--color-text-dim)] font-mono">No phase data available.</p>;
  }

  return (
    <div className="w-full space-y-4">
      {/* Bar chart */}
      <div className="flex items-end gap-1.5 h-28">
        {groups.map((g, idx) => {
          const heightPct = maxVel > 0 ? Math.max((g.avgVelocity / maxVel) * 100, 4) : 4;
          const color = PHASE_COLORS[g.phase] ?? "#666";
          return (
            <div
              key={g.phase}
              className="flex-1 flex flex-col items-center justify-end h-full gap-0.5"
            >
              <div className="relative w-full flex justify-center items-end h-full">
                {g.hasLeak && (
                  <span
                    className="absolute text-[var(--color-red)] text-[11px] font-bold"
                    style={{ top: `calc(${100 - heightPct}% - 18px)` }}
                  >
                    ↯
                  </span>
                )}
                <div
                  className="w-full rounded-t-sm"
                  style={{
                    height: `${heightPct}%`,
                    backgroundColor: color,
                    opacity: g.hasLeak ? 1 : 0.75,
                    boxShadow: g.hasLeak ? `0 -2px 8px ${color}66` : undefined,
                    animationDelay: `${idx * 60}ms`,
                    animation: `bar-grow 0.4s cubic-bezier(0.16, 1, 0.3, 1) both`,
                    animationDelay: `${idx * 50}ms`,
                  }}
                />
              </div>
              <p
                className="text-[9px] uppercase tracking-wider truncate w-full text-center"
                style={{ color, fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}
              >
                {g.label}
              </p>
            </div>
          );
        })}
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--color-border)]" />

      {/* Insight lines */}
      <div className="space-y-2.5">
        {groups.filter((g) => g.hasLeak || g.phase === "contact").map((g) => (
          <div key={g.phase} className="flex items-start gap-2.5">
            <span
              className="mt-0.5 shrink-0 text-sm font-bold"
              style={{ color: g.hasLeak ? "var(--color-red)" : "var(--color-accent)" }}
            >
              {g.hasLeak ? "↯" : "✓"}
            </span>
            <p className="text-sm leading-snug text-[var(--color-text-dim)]">
              <span
                className="font-semibold"
                style={{ color: PHASE_COLORS[g.phase], fontFamily: "Barlow Condensed, sans-serif", fontSize: "0.8rem", letterSpacing: "0.4px" }}
              >
                {g.label.toUpperCase()}:{" "}
              </span>
              {phaseInsight(g, groups)}
            </p>
          </div>
        ))}
        {groups.every((g) => !g.hasLeak) && (
          <div className="flex items-start gap-2.5">
            <span className="mt-0.5 text-sm font-bold text-[var(--color-accent)]">✓</span>
            <p className="text-sm text-[var(--color-text-dim)]">No major power leaks detected in this swing.</p>
          </div>
        )}
      </div>
    </div>
  );
}
