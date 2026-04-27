import { useMemo } from "react";
import type { EnergyLossEvent, Frame3D } from "@/lib/api";
import { PHASE_COLORS } from "@/lib/metrics";

const PHASE_LABELS: Record<string, string> = {
  idle: "Idle",
  stance: "Set Up",
  load: "Load",
  launch: "Launch",
  stride: "Stride",
  swing: "Turn",
  contact: "Contact",
  follow_through: "Finish",
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

  if (group.hasLeak) return "You lost speed here.";
  if (group.phase === "contact") {
    return group.avgVelocity > 0 ? "Power carried into contact here." : "This phase is too short to read clearly.";
  }
  if (prev && group.avgVelocity > prev.avgVelocity * 1.1) return "Power built well here.";
  if (prev && group.avgVelocity < prev.avgVelocity * 0.85) return "Speed backed up here.";
  return "Power held steady here.";
}

interface Props {
  frames: Frame3D[];
  phaseLabels: string[];
  energyLossEvents: EnergyLossEvent[];
}

export function PhaseEnergyChart({ frames, phaseLabels, energyLossEvents }: Props) {
  const leakFrames = useMemo(
    () => new Set(energyLossEvents.filter((event) => event.magnitude_pct > 30).map((event) => event.frame)),
    [energyLossEvents],
  );

  const groups = useMemo<PhaseGroup[]>(() => {
    const map = new Map<string, { total: number; count: number; hasLeak: boolean }>();
    const order: string[] = [];

    phaseLabels.forEach((phase, index) => {
      if (!map.has(phase)) {
        map.set(phase, { total: 0, count: 0, hasLeak: false });
        order.push(phase);
      }
      const entry = map.get(phase)!;
      const velocity = frames[index]?.velocities?.right_wrist ?? frames[index]?.velocities?.left_wrist ?? 0;
      entry.total += velocity;
      entry.count += 1;
      if (leakFrames.has(index)) entry.hasLeak = true;
    });

    return order
      .filter((phase) => phase !== "idle")
      .map((phase) => {
        const entry = map.get(phase)!;
        return {
          phase,
          label: PHASE_LABELS[phase] ?? phase,
          avgVelocity: entry.count ? entry.total / entry.count : 0,
          frameCount: entry.count,
          hasLeak: entry.hasLeak,
        };
      });
  }, [frames, leakFrames, phaseLabels]);

  const maxVelocity = useMemo(() => Math.max(...groups.map((group) => group.avgVelocity), 1), [groups]);

  if (groups.length === 0) {
    return <p className="text-sm text-[var(--color-text-dim)]">Speed data unavailable.</p>;
  }

  return (
    <div className="w-full space-y-5">
      <div className="flex h-32 items-end gap-2">
        {groups.map((group, index) => {
          const heightPct = maxVelocity > 0 ? Math.max((group.avgVelocity / maxVelocity) * 100, 4) : 4;
          const color = PHASE_COLORS[group.phase] ?? "#666";
          return (
            <div key={group.phase} className="flex h-full flex-1 flex-col items-center justify-end gap-1.5">
              <div className="relative flex h-full w-full items-end justify-center">
                {group.hasLeak ? (
                  <span
                    className="absolute text-sm font-bold text-[var(--color-red)]"
                    style={{ top: `calc(${100 - heightPct}% - 20px)` }}
                  >
                    !
                  </span>
                ) : null}
                <div
                  className="w-full rounded-t-md"
                  style={{
                    height: `${heightPct}%`,
                    backgroundColor: color,
                    opacity: group.hasLeak ? 1 : 0.82,
                    boxShadow: group.hasLeak ? `0 -2px 10px ${color}55` : undefined,
                    animation: `bar-grow 0.4s cubic-bezier(0.16, 1, 0.3, 1) both`,
                    animationDelay: `${index * 45}ms`,
                  }}
                />
              </div>
              <p className="w-full text-center text-[11px] font-semibold" style={{ color }}>
                {group.label}
              </p>
            </div>
          );
        })}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {groups.map((group) => (
          <div
            key={`${group.phase}-insight`}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)]/50 p-3"
          >
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: PHASE_COLORS[group.phase] ?? "#666" }} />
              <p className="text-sm font-semibold text-[var(--color-text)]">{group.label}</p>
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--color-text-dim)]">{phaseInsight(group, groups)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
