import { PHASE_COLORS, PHASE_LABELS } from "@/lib/metrics";

interface PhaseTimelineProps {
  phaseLabels: string[];
  phaseDurations?: Record<string, number>;
  totalFrames?: number;
  contactFrame?: number | null;
  stridePlantFrame?: number | null;
  currentFrame?: number;
  onFrameSelect?: (frame: number) => void;
}

interface TimelineSegment {
  phase: string;
  start: number;
  width: number;
}

const PHASE_EXPLANATIONS: Record<string, string> = {
  idle: "Setup frames before the move begins.",
  stance: "Starting position before the body begins loading.",
  load: "Gathering move that stores tension before the swing starts forward.",
  launch: "Transition out of the load as the move starts heading into contact.",
  stride: "Move into foot strike so the body can brace before rotation.",
  swing: "Rotational move that sends the barrel into the zone.",
  contact: "Barrel enters the hit window and meets the ball.",
  follow_through: "Deceleration pattern after contact shows how the swing finished.",
};

function clampFrame(frame: number, totalFrames: number): number {
  if (totalFrames <= 1) return 0;
  return Math.min(Math.max(Math.round(frame), 0), totalFrames - 1);
}

function buildSegments(
  phaseLabels: string[],
  phaseDurations: Record<string, number> | undefined,
  totalFrames: number,
): TimelineSegment[] {
  if (phaseLabels.length === 0) return [];

  if (phaseLabels.length === totalFrames) {
    const segments: TimelineSegment[] = [];
    let index = 0;
    while (index < totalFrames) {
      const phase = phaseLabels[index];
      let end = index;
      while (end < totalFrames && phaseLabels[end] === phase) end++;
      segments.push({ phase, start: index, width: end - index });
      index = end;
    }
    return segments;
  }

  const orderedPhases = phaseLabels.filter((phase, index) => phase && phaseLabels.indexOf(phase) === index);
  if (orderedPhases.length === 0) return [];

  const durationTotal = orderedPhases.reduce((sum, phase) => sum + (phaseDurations?.[phase] ?? 0), 0);
  const segments: TimelineSegment[] = [];
  let cursor = 0;

  orderedPhases.forEach((phase, index) => {
    const remainingFrames = totalFrames - cursor;
    const remainingPhases = orderedPhases.length - index - 1;
    const rawWidth =
      index === orderedPhases.length - 1
        ? remainingFrames
        : durationTotal > 0
          ? Math.round(((phaseDurations?.[phase] ?? 0) / durationTotal) * totalFrames)
          : Math.round(totalFrames / orderedPhases.length);
    const width = Math.max(1, Math.min(rawWidth, remainingFrames - remainingPhases));

    segments.push({ phase, start: cursor, width });
    cursor += width;
  });

  return segments;
}

function markerPosition(frame: number, totalFrames: number): string {
  if (totalFrames <= 1) return "0%";
  return `${(clampFrame(frame, totalFrames) / (totalFrames - 1)) * 100}%`;
}

export function PhaseTimeline({
  phaseLabels,
  phaseDurations,
  totalFrames,
  contactFrame,
  stridePlantFrame,
  currentFrame,
  onFrameSelect,
}: PhaseTimelineProps) {
  const total = Math.max(totalFrames ?? phaseLabels.length, phaseLabels.length, 1);
  const segments = buildSegments(phaseLabels, phaseDurations, total);
  if (segments.length === 0) return null;

  const selectedFrame = currentFrame === undefined ? 0 : clampFrame(currentFrame, total);
  const selectedSegment = segments.find(
    (segment) => selectedFrame >= segment.start && selectedFrame < segment.start + segment.width,
  );
  const selectedPhaseLabel = selectedSegment ? PHASE_LABELS[selectedSegment.phase] ?? selectedSegment.phase.replaceAll("_", " ") : "";
  const helperText = selectedSegment
    ? `${selectedPhaseLabel}: ${PHASE_EXPLANATIONS[selectedSegment.phase] ?? "Phase guidance unavailable."}`
    : "Select a phase to jump the annotated video.";
  const markers = [
    stridePlantFrame !== null && stridePlantFrame !== undefined
      ? { label: "Stride plant", frame: stridePlantFrame }
      : null,
    contactFrame !== null && contactFrame !== undefined ? { label: "Contact", frame: contactFrame } : null,
  ].filter((marker): marker is { label: string; frame: number } => Boolean(marker));

  return (
    <div className="w-full space-y-3">
      <div className="relative pt-8">
        {markers.map((marker) => (
          <span
            key={marker.label}
            className="absolute top-0 z-30 -translate-x-1/2 rounded-full border border-white/10 bg-[var(--color-surface)] px-2 py-1 text-[10px] font-medium uppercase tracking-[0.16em] text-[var(--color-text-dim)]"
            style={{ left: markerPosition(marker.frame, total) }}
          >
            {marker.label}
          </span>
        ))}

        <div className="relative flex h-12 overflow-hidden rounded-xl border border-white/10 bg-[var(--color-surface-2)]/35">
          {markers.map((marker) => (
            <span
              key={`${marker.label}-line`}
              aria-hidden="true"
              className="pointer-events-none absolute inset-y-0 z-20 w-0.5 -translate-x-1/2 bg-white/80"
              style={{ left: markerPosition(marker.frame, total) }}
            />
          ))}

          {segments.map((segment, index) => {
            const isSelected = selectedFrame >= segment.start && selectedFrame < segment.start + segment.width;
            const explanation = PHASE_EXPLANATIONS[segment.phase] ?? "Phase guidance unavailable.";
            const phaseLabel = PHASE_LABELS[segment.phase] ?? segment.phase.replaceAll("_", " ");

            return (
              <button
                key={`${segment.phase}-${index}`}
                type="button"
                className={`group relative flex h-full items-center justify-center px-1 text-[11px] font-semibold transition focus:outline-none focus-visible:z-30 focus-visible:ring-2 focus-visible:ring-white/90 sm:px-2 sm:text-xs ${
                  isSelected ? "z-10 shadow-[inset_0_0_0_2px_rgba(255,255,255,0.9)]" : "hover:opacity-90"
                }`}
                style={{
                  width: `${(segment.width / total) * 100}%`,
                  backgroundColor: PHASE_COLORS[segment.phase] || "#555555",
                }}
                onClick={() => onFrameSelect?.(segment.start)}
                aria-label={`${phaseLabel}: ${explanation} Frames ${segment.start} to ${segment.start + segment.width - 1}.`}
                aria-pressed={isSelected}
                title={`${phaseLabel}: ${explanation}`}
              >
                {segment.width / total > 0.08 && (
                  <span className="pointer-events-none absolute inset-0 flex items-center justify-center px-1 text-center leading-tight text-black/80">
                    {phaseLabel}
                  </span>
                )}
                <span className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-44 -translate-x-1/2 rounded-lg border border-white/10 bg-[var(--color-surface)] px-3 py-2 text-left text-[11px] leading-4 text-[var(--color-text)] opacity-0 shadow-lg transition group-hover:opacity-100 group-focus-visible:opacity-100">
                  {explanation}
                </span>
              </button>
            );
          })}

          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-0 z-20 w-1 -translate-x-1/2 rounded-full bg-white shadow-[0_0_0_2px_rgba(15,20,30,0.65)] transition-all duration-100"
            style={{ left: markerPosition(selectedFrame, total) }}
          />
        </div>
      </div>

      <p className="text-sm leading-6 text-[var(--color-text-dim)]">{helperText}</p>
    </div>
  );
}
