import { METRIC_RANGES, metricZone } from "./metrics";
import type { SwingMetrics } from "./api";

const ZONE_POINTS: Record<"good" | "moderate" | "poor", number> = {
  good: 100,
  moderate: 60,
  poor: 20,
};

// Keys that contribute to the overall score, in priority order.
// wrist_peak_velocity_px_s excluded — pixel units vary too much by camera distance.
const SCORED_METRICS: Array<keyof typeof METRIC_RANGES> = [
  "x_factor_at_contact",
  "hip_angle_at_contact",
  "shoulder_angle_at_contact",
  "spine_tilt_at_contact",
  "left_knee_at_contact",
  "right_knee_at_contact",
  "head_displacement_total",
];

/**
 * Compute an overall swing score 0–100.
 *
 * @param metrics  Real metrics from the analysis report.
 * @param overrides  Hypothetical values that replace real ones (for What-If).
 */
export function computeScore(
  metrics: Partial<SwingMetrics>,
  overrides: Partial<Record<string, number>> = {}
): number {
  let total = 0;
  let count = 0;

  for (const key of SCORED_METRICS) {
    const value = overrides[key] ?? (metrics as Record<string, unknown>)[key];
    if (typeof value !== "number" || !isFinite(value)) continue;
    total += ZONE_POINTS[metricZone(key, value)];
    count++;
  }

  if (count === 0) return 0;
  return Math.round(total / count);
}

/**
 * Human-readable label for a score band.
 */
export function scoreLabel(score: number): { label: string; color: string } {
  if (score >= 80) return { label: "Elite",        color: "#00FF87" };
  if (score >= 65) return { label: "Above Average", color: "#00CC6A" };
  if (score >= 50) return { label: "Average",       color: "#D4A017" };
  if (score >= 35) return { label: "Below Average", color: "#FF8A00" };
  return              { label: "Needs Work",      color: "#FF4444" };
}
