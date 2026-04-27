import { useMemo } from "react";
import type { Frame3D } from "@/lib/api";

const HIP_LEFT = 11;
const HIP_RIGHT = 12;
const SHOULDER_LEFT = 5;
const SHOULDER_RIGHT = 6;

function normalizeAngle(angle: number): number {
  let value = angle;
  while (value > 180) value -= 360;
  while (value < -180) value += 360;
  return value;
}

function yawAngle(keypoints: number[][], a: number, b: number): number | null {
  const pa = keypoints[a];
  const pb = keypoints[b];
  if (!pa || !pb) return null;
  if ([pa[0], pa[2], pb[0], pb[2]].some((value) => !Number.isFinite(value))) return null;
  return Math.atan2(pb[2] - pa[2], pb[0] - pa[0]) * (180 / Math.PI);
}

function hipShoulderSeparation(frame: Frame3D): number | null {
  const hip = yawAngle(frame.keypoints, HIP_LEFT, HIP_RIGHT);
  const shoulder = yawAngle(frame.keypoints, SHOULDER_LEFT, SHOULDER_RIGHT);
  if (hip == null || shoulder == null) return null;
  return Math.round(normalizeAngle(hip - shoulder));
}

interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

function collectBounds(frames: Frame3D[]): Bounds | null {
  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  for (const frame of frames) {
    for (const keypoint of frame.keypoints) {
      const [x, y] = keypoint;
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    }
    if (frame.bat) {
      for (const point of [frame.bat.handle, frame.bat.barrel]) {
        const [x, y] = point;
        if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
      }
    }
  }

  if (![minX, maxX, minY, maxY].every(Number.isFinite)) return null;
  if (minX === maxX || minY === maxY) return null;
  return { minX, maxX, minY, maxY };
}

function projectPoint(
  point: number[] | undefined,
  bounds: Bounds,
  width: number,
  height: number,
  padding: number,
): [number, number] | null {
  if (!point) return null;
  const [x, y] = point;
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const px = padding + ((x - bounds.minX) / (bounds.maxX - bounds.minX || 1)) * usableWidth;
  const normalizedY = padding + ((y - bounds.minY) / (bounds.maxY - bounds.minY || 1)) * usableHeight;
  return [px, height - normalizedY];
}

function phaseLabel(phase: string): string {
  return phase.replaceAll("_", " ");
}

interface Props {
  frames: Frame3D[];
  currentFrame: number;
  contactFrame: number;
}

export function AnimatedSwingReplay({ frames, currentFrame, contactFrame }: Props) {
  const width = 620;
  const height = 360;
  const padding = 28;
  const safeFrameIndex = Math.min(Math.max(currentFrame, 0), Math.max(frames.length - 1, 0));
  const frame = frames[safeFrameIndex];
  const bounds = useMemo(() => collectBounds(frames), [frames]);

  const trailFrames = useMemo(() => {
    const start = Math.max(0, safeFrameIndex - 5);
    return frames.slice(start, safeFrameIndex + 1);
  }, [frames, safeFrameIndex]);

  if (!frame || !bounds) {
    return <div className="flex h-[320px] items-center justify-center text-sm text-[var(--color-text-dim)]">No frame data available</div>;
  }

  const separation = hipShoulderSeparation(frame);
  const batVisible = trailFrames.some((entry) => (entry.bat?.confidence ?? 0) > 0.25);

  return (
    <div className="space-y-4" data-testid="animated-swing-replay">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1 text-xs font-medium text-[var(--color-text)]">
          Replay
        </span>
        <span className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1 text-xs font-medium text-[var(--color-text-dim)]">
          {phaseLabel(frame.phase)}
        </span>
        <span className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1 text-xs font-medium text-[var(--color-text-dim)]">
          Frame {safeFrameIndex + 1} / {frames.length}
        </span>
        {safeFrameIndex >= contactFrame ? (
          <span className="rounded-full border border-[var(--color-accent)]/30 bg-[var(--color-accent)]/10 px-3 py-1 text-xs font-medium text-[var(--color-accent)]">
            Contact reached
          </span>
        ) : null}
      </div>

      <div className="overflow-hidden rounded-[22px] border border-[var(--color-border)] bg-[linear-gradient(180deg,rgba(8,12,18,0.96),rgba(16,22,30,0.92))]">
        <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Animated swing replay">
          <defs>
            <linearGradient id="batPathGradient" x1="0%" x2="100%" y1="0%" y2="0%">
              <stop offset="0%" stopColor="#8ec5ff" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#8ec5ff" stopOpacity="0.9" />
            </linearGradient>
          </defs>

          {trailFrames.map((trailFrame, trailIndex) => {
            const opacity = 0.18 + (trailIndex / Math.max(trailFrames.length, 1)) * 0.5;
            const isCurrent = trailIndex === trailFrames.length - 1;

            return (
              <g key={`${trailFrame.phase}-${trailIndex}`}>
                {trailFrame.skeleton.map(([fromIndex, toIndex], edgeIndex) => {
                  const start = projectPoint(trailFrame.keypoints[fromIndex], bounds, width, height, padding);
                  const end = projectPoint(trailFrame.keypoints[toIndex], bounds, width, height, padding);
                  if (!start || !end) return null;
                  return (
                    <line
                      key={`${trailIndex}-${edgeIndex}`}
                      x1={start[0]}
                      y1={start[1]}
                      x2={end[0]}
                      y2={end[1]}
                      stroke={isCurrent ? "#f5f7fb" : "#6f7d90"}
                      strokeLinecap="round"
                      strokeOpacity={opacity}
                      strokeWidth={isCurrent ? 3.4 : 2.1}
                    />
                  );
                })}

                {trailFrame.keypoints.map((keypoint, keypointIndex) => {
                  const point = projectPoint(keypoint, bounds, width, height, padding);
                  if (!point) return null;
                  return (
                    <circle
                      key={`${trailIndex}-kp-${keypointIndex}`}
                      cx={point[0]}
                      cy={point[1]}
                      r={isCurrent ? 3.1 : 2.2}
                      fill={isCurrent ? "#00d084" : "#91a0b6"}
                      fillOpacity={opacity}
                    />
                  );
                })}

                {trailFrame.bat ? (() => {
                  const handle = projectPoint(trailFrame.bat.handle, bounds, width, height, padding);
                  const barrel = projectPoint(trailFrame.bat.barrel, bounds, width, height, padding);
                  if (!handle || !barrel) return null;
                  return (
                    <g>
                      <line
                        x1={handle[0]}
                        y1={handle[1]}
                        x2={barrel[0]}
                        y2={barrel[1]}
                        stroke={isCurrent ? "#ffd166" : "url(#batPathGradient)"}
                        strokeLinecap="round"
                        strokeOpacity={Math.max(opacity, 0.35)}
                        strokeWidth={isCurrent ? 5 : 3}
                      />
                      <circle
                        cx={barrel[0]}
                        cy={barrel[1]}
                        r={isCurrent ? 4 : 3}
                        fill="#ffd166"
                        fillOpacity={Math.max(opacity, 0.35)}
                      />
                    </g>
                  );
                })() : null}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-[18px] border border-[var(--color-border)] bg-[var(--color-surface-2)]/70 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--color-text-dim)]">What you are seeing</p>
          <p className="mt-2 text-sm leading-6 text-[var(--color-text)]">
            A frame-by-frame body replay with the recent path ghosted behind it, so the move reads like motion instead of a frozen pose.
          </p>
        </div>
        <div className="rounded-[18px] border border-[var(--color-border)] bg-[var(--color-surface-2)]/70 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--color-text-dim)]">Bat path</p>
          <p className="mt-2 text-sm leading-6 text-[var(--color-text)]">
            {batVisible ? "The gold bat line shows the current bat estimate, with recent barrel travel left behind it." : "Bat path is not reliable on this frame yet, so the replay leans on body motion first."}
          </p>
        </div>
        <div className="rounded-[18px] border border-[var(--color-border)] bg-[var(--color-surface-2)]/70 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--color-text-dim)]">Turn snapshot</p>
          <p className="mt-2 text-sm leading-6 text-[var(--color-text)]">
            {separation == null
              ? "Hip and shoulder turn are not readable on this frame."
              : `Hip-shoulder separation is ${Math.abs(separation)} degrees ${separation >= 0 ? "with the hips leading" : "with the shoulders leading"}.`}
          </p>
        </div>
      </div>
    </div>
  );
}
