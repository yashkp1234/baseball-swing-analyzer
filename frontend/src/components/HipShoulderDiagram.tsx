import { useMemo } from "react";
import type { Frame3D } from "@/lib/api";

const L_HIP = 11;
const R_HIP = 12;
const L_SHOULDER = 5;
const R_SHOULDER = 6;

function yawAngle(kp: number[][], a: number, b: number): number | null {
  const pa = kp[a];
  const pb = kp[b];
  if (!pa || !pb) return null;
  if ([pa[0], pa[2], pb[0], pb[2]].some((value) => !Number.isFinite(value))) return null;
  return Math.atan2(pb[2] - pa[2], pb[0] - pa[0]) * (180 / Math.PI);
}

function arcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number): string {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const x1 = cx + r * Math.cos(toRad(startDeg));
  const y1 = cy + r * Math.sin(toRad(startDeg));
  const x2 = cx + r * Math.cos(toRad(endDeg));
  const y2 = cy + r * Math.sin(toRad(endDeg));
  const largeArc = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
}

function normalizeAngle(angle: number): number {
  let value = angle;
  while (value > 180) value -= 360;
  while (value < -180) value += 360;
  return value;
}

interface Props {
  frames: Frame3D[];
  currentFrame: number;
  contactFrame: number;
}

export function HipShoulderDiagram({ frames, currentFrame, contactFrame }: Props) {
  const baseline = useMemo(() => {
    const frame = frames[0];
    if (!frame?.keypoints?.length) return null;
    return {
      hip: yawAngle(frame.keypoints, L_HIP, R_HIP),
      shoulder: yawAngle(frame.keypoints, L_SHOULDER, R_SHOULDER),
    };
  }, [frames]);

  const current = useMemo(() => {
    const frame = frames[Math.min(currentFrame, Math.max(frames.length - 1, 0))];
    if (!frame?.keypoints?.length) return null;
    return {
      hip: yawAngle(frame.keypoints, L_HIP, R_HIP),
      shoulder: yawAngle(frame.keypoints, L_SHOULDER, R_SHOULDER),
    };
  }, [currentFrame, frames]);

  const missingGeometry =
    baseline?.hip == null || baseline?.shoulder == null ||
    current?.hip == null || current?.shoulder == null;

  if (!frames.length) {
    return <div className="flex h-40 items-center justify-center text-sm text-[var(--color-text-dim)]">No frame data available</div>;
  }

  if (missingGeometry) {
    return (
      <div className="flex h-40 flex-col items-center justify-center gap-2">
        <div className="text-2xl opacity-40">◎</div>
        <p className="text-sm text-[var(--color-text-dim)]">Insufficient 3D joint data for this frame</p>
      </div>
    );
  }

  const hipStart = baseline.hip as number;
  const shoulderStart = baseline.shoulder as number;
  const hipCurrent = current.hip as number;
  const shoulderCurrent = current.shoulder as number;
  const hipDelta = hipCurrent - hipStart;
  const shoulderDelta = shoulderCurrent - shoulderStart;
  const separation = Math.round(normalizeAngle(hipDelta - shoulderDelta));
  const separationColor = separation >= 20 ? "#00FF87" : separation >= 5 ? "#FFD54A" : "#FF6B6B";
  const separationLabel =
    separation > 5
      ? `Hips led shoulders by ${Math.abs(separation)}°`
      : separation < -5
        ? `Shoulders outran hips by ${Math.abs(separation)}°`
        : "Hips and shoulders stayed mostly synced";

  const cx = 120;
  const cy = 120;
  const hipRadius = 72;
  const shoulderRadius = 50;
  const hipEnd = hipStart + hipDelta;
  const shoulderEnd = shoulderStart + shoulderDelta;

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width={240} height={240} viewBox="0 0 240 240" className="overflow-visible">
        <circle cx={cx} cy={cy} r={hipRadius + 14} fill="none" stroke="#1d2430" strokeWidth={1} />
        <circle cx={cx} cy={cy} r={shoulderRadius + 14} fill="none" stroke="#16202a" strokeDasharray="3 5" strokeWidth={1} />
        {Array.from({ length: 12 }).map((_, index) => {
          const angle = (index * 30 * Math.PI) / 180;
          const r1 = hipRadius + 8;
          const r2 = hipRadius + 14;
          return (
            <line
              key={index}
              x1={cx + r1 * Math.cos(angle)}
              y1={cy + r1 * Math.sin(angle)}
              x2={cx + r2 * Math.cos(angle)}
              y2={cy + r2 * Math.sin(angle)}
              stroke="#2a3342"
              strokeWidth={1}
            />
          );
        })}
        <circle cx={cx} cy={cy} r={3} fill="#2A3240" />
        {Math.abs(hipDelta) > 0.5 ? (
          <path d={arcPath(cx, cy, hipRadius, hipStart, hipEnd)} fill="none" stroke="#ff6b6b" strokeLinecap="round" strokeWidth={6} />
        ) : null}
        {Math.abs(shoulderDelta) > 0.5 ? (
          <path d={arcPath(cx, cy, shoulderRadius, shoulderStart, shoulderEnd)} fill="none" stroke="#4A90D9" strokeLinecap="round" strokeWidth={6} />
        ) : null}
        {currentFrame >= contactFrame ? (
          <>
            <circle cx={cx} cy={cy} r={hipRadius + 5} fill="none" stroke="#ffd54a" strokeDasharray="4 4" strokeWidth={1.5} opacity={0.8} />
            <text x={cx} y={18} fill="#ffd54a" fontFamily="DM Mono, monospace" fontSize={9} opacity={0.8} textAnchor="middle">
              CONTACT
            </text>
          </>
        ) : null}
      </svg>

      <div className="space-y-1 text-center">
        <p className="text-sm font-semibold" style={{ color: separationColor, fontFamily: "Barlow Condensed, sans-serif", letterSpacing: "0.5px" }}>
          {separationLabel}
        </p>
        <p className="text-xs text-[var(--color-text-dim)]" style={{ fontFamily: "DM Mono, monospace" }}>
          TOP-DOWN YAW · FRAME {currentFrame + 1}/{frames.length}
        </p>
      </div>
    </div>
  );
}
