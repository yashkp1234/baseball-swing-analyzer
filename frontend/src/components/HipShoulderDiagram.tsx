import { useMemo } from "react";
import type { Frame3D } from "@/lib/api";

const L_HIP = 11, R_HIP = 12, L_SHOULDER = 5, R_SHOULDER = 6;
const MIN_CONFIDENCE = 0.2;

function axisAngle(kp: number[][], a: number, b: number): number | null {
  const pa = kp[a], pb = kp[b];
  if (!pa || !pb) return null;
  if ((pa[2] ?? 0) < MIN_CONFIDENCE || (pb[2] ?? 0) < MIN_CONFIDENCE) return null;
  return Math.atan2(pb[1] - pa[1], pb[0] - pa[0]) * (180 / Math.PI);
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

interface Props {
  frames: Frame3D[];
  currentFrame: number;
  contactFrame: number;
}

export function HipShoulderDiagram({ frames, currentFrame, contactFrame }: Props) {
  const CX = 120, CY = 120, R_HIP_ARC = 70, R_SHOULDER_ARC = 50;

  const baseline = useMemo(() => {
    const f = frames[0];
    if (!f?.keypoints?.length) return null;
    const hip = axisAngle(f.keypoints, L_HIP, R_HIP);
    const shoulder = axisAngle(f.keypoints, L_SHOULDER, R_SHOULDER);
    return { hip, shoulder };
  }, [frames]);

  const current = useMemo(() => {
    if (!frames.length) return null;
    const f = frames[Math.min(currentFrame, frames.length - 1)];
    if (!f?.keypoints?.length) return null;
    const hip = axisAngle(f.keypoints, L_HIP, R_HIP);
    const shoulder = axisAngle(f.keypoints, L_SHOULDER, R_SHOULDER);
    return { hip, shoulder };
  }, [frames, currentFrame]);

  // Use explicit null checks (not truthy) to avoid zero-angle false negatives
  const lowConfidence =
    baseline?.hip == null || baseline?.shoulder == null ||
    current?.hip == null || current?.shoulder == null;

  const hipDelta = lowConfidence ? 0 : (current!.hip! - baseline!.hip!);
  const shoulderDelta = lowConfidence ? 0 : (current!.shoulder! - baseline!.shoulder!);
  const separation = Math.round(hipDelta - shoulderDelta);

  const separationLabel =
    separation > 5
      ? `Hips led by ${Math.abs(separation)}° — good separation`
      : separation < -5
      ? `Shoulders leading hips by ${Math.abs(separation)}° — work on this`
      : "Hips and shoulders moving together";

  const separationColor =
    separation >= 20 ? "#00FF87" : separation >= 5 ? "#D4A017" : "#FF4444";

  const hipStartAngle = baseline?.hip ?? 0;
  const hipEndAngle = hipStartAngle + hipDelta;
  const shoulderStartAngle = baseline?.shoulder ?? 0;
  const shoulderEndAngle = shoulderStartAngle + shoulderDelta;

  if (!frames.length) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-[var(--color-text-dim)]">
        No frame data available
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3">
      {lowConfidence ? (
        <div className="flex flex-col items-center justify-center h-40 gap-2">
          <div className="text-2xl opacity-40">◎</div>
          <p className="text-sm text-[var(--color-text-dim)]">Low pose confidence — diagram unavailable</p>
        </div>
      ) : (
        <svg width={240} height={240} viewBox="0 0 240 240" className="overflow-visible">
          {/* Outer ring */}
          <circle cx={CX} cy={CY} r={R_HIP_ARC + 14} fill="none" stroke="#1E2530" strokeWidth={1} />
          {/* Inner ring dashed */}
          <circle cx={CX} cy={CY} r={R_SHOULDER_ARC + 14} fill="none" stroke="#1A1E24" strokeWidth={1} strokeDasharray="3 5" />

          {/* Radial tick marks */}
          {Array.from({ length: 12 }).map((_, i) => {
            const angle = (i * 30 * Math.PI) / 180;
            const r1 = R_HIP_ARC + 8, r2 = R_HIP_ARC + 14;
            return (
              <line
                key={i}
                x1={CX + r1 * Math.cos(angle)} y1={CY + r1 * Math.sin(angle)}
                x2={CX + r2 * Math.cos(angle)} y2={CY + r2 * Math.sin(angle)}
                stroke="#2A3240" strokeWidth={1}
              />
            );
          })}

          {/* Center dot */}
          <circle cx={CX} cy={CY} r={3} fill="#2A3240" />
          <circle cx={CX} cy={CY} r={1.5} fill="#4A5568" />

          {/* Hip arc — red/coral */}
          {Math.abs(hipDelta) > 0.5 && (
            <path
              d={arcPath(CX, CY, R_HIP_ARC, hipStartAngle, hipEndAngle)}
              fill="none"
              stroke="#FF3B3B"
              strokeWidth={6}
              strokeLinecap="round"
              opacity={0.9}
            />
          )}

          {/* Shoulder arc — blue */}
          {Math.abs(shoulderDelta) > 0.5 && (
            <path
              d={arcPath(CX, CY, R_SHOULDER_ARC, shoulderStartAngle, shoulderEndAngle)}
              fill="none"
              stroke="#4A90D9"
              strokeWidth={6}
              strokeLinecap="round"
              opacity={0.9}
            />
          )}

          {/* Contact frame ring */}
          {currentFrame >= contactFrame && (
            <>
              <circle
                cx={CX} cy={CY} r={R_HIP_ARC + 4}
                fill="none"
                stroke="#FFD700"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                opacity={0.6}
              />
              <text x={CX} y={18} textAnchor="middle" fill="#FFD700" fontSize={9} fontFamily="DM Mono, monospace" opacity={0.8}>
                CONTACT
              </text>
            </>
          )}

          {/* Legend */}
          <rect x={8} y={212} width={8} height={8} rx={2} fill="#FF3B3B" opacity={0.9} />
          <text x={20} y={220} fill="#6B7A8D" fontSize={9} fontFamily="Barlow Condensed, sans-serif" letterSpacing="0.5">HIPS</text>
          <rect x={58} y={212} width={8} height={8} rx={2} fill="#4A90D9" opacity={0.9} />
          <text x={70} y={220} fill="#6B7A8D" fontSize={9} fontFamily="Barlow Condensed, sans-serif" letterSpacing="0.5">SHOULDERS</text>
        </svg>
      )}

      <div className="text-center space-y-1">
        <p className="text-sm font-semibold" style={{ color: separationColor, fontFamily: "Barlow Condensed, sans-serif", letterSpacing: "0.5px" }}>
          {separationLabel}
        </p>
        <p className="text-xs text-[var(--color-text-dim)]" style={{ fontFamily: "DM Mono, monospace" }}>
          TOP-DOWN VIEW · FRAME {currentFrame + 1}/{frames.length}
        </p>
      </div>
    </div>
  );
}
