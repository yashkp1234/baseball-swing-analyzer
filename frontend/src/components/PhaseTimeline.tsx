import { PHASE_COLORS, type MetricRange } from "@/lib/metrics";

interface PhaseTimelineProps {
  phaseLabels: string[];
  currentFrame?: number;
  onFrameSelect?: (frame: number) => void;
}

export function PhaseTimeline({ phaseLabels, currentFrame, onFrameSelect }: PhaseTimelineProps) {
  const total = phaseLabels.length;
  if (total === 0) return null;

  const segments: { phase: string; start: number; width: number }[] = [];
  let i = 0;
  while (i < total) {
    const phase = phaseLabels[i];
    let j = i;
    while (j < total && phaseLabels[j] === phase) j++;
    segments.push({ phase, start: i, width: j - i });
    i = j;
  }

  return (
    <div className="w-full">
      <div className="flex rounded-lg overflow-hidden h-8">
        {segments.map((seg, idx) => (
          <div
            key={`${seg.phase}-${idx}`}
            className="relative cursor-pointer transition-opacity hover:opacity-90"
            style={{
              width: `${(seg.width / total) * 100}%`,
              backgroundColor: PHASE_COLORS[seg.phase] || "#555",
            }}
            onClick={() => onFrameSelect?.(seg.start)}
            title={`${seg.phase}: frames ${seg.start}–${seg.start + seg.width - 1}`}
          >
            {seg.width / total > 0.08 && (
              <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-black/80">
                {seg.phase}
              </span>
            )}
          </div>
        ))}
      </div>
      {currentFrame !== undefined && (
        <div
          className="h-1 bg-[var(--color-accent)] rounded-full mt-1 transition-all duration-100"
          style={{ width: `${(currentFrame / total) * 100}%` }}
        />
      )}
    </div>
  );
}