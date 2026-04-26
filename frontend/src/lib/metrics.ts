export interface MetricRange {
  good: [number, number];
  moderate: [number, number];
  unit?: string;
}

export const METRIC_RANGES: Record<string, MetricRange> = {
  x_factor_at_contact: { good: [20, 45], moderate: [10, 55], unit: "°" },
  hip_angle_at_contact: { good: [160, 190], moderate: [140, 200], unit: "°" },
  shoulder_angle_at_contact: { good: [140, 180], moderate: [120, 200], unit: "°" },
  spine_tilt_at_contact: { good: [5, 20], moderate: [0, 30], unit: "°" },
  left_knee_at_contact: { good: [20, 50], moderate: [0, 70], unit: "°" },
  right_knee_at_contact: { good: [20, 50], moderate: [0, 70], unit: "°" },
  head_displacement_total: { good: [0, 30], moderate: [0, 60], unit: "px" },
  wrist_peak_velocity_px_s: { good: [1000, 3000], moderate: [500, 4000], unit: "px/s" },
};

export const PHASE_COLORS: Record<string, string> = {
  idle: "#555555",
  stance: "#4A90D9",
  load: "#00CC6A",
  stride: "#D4A017",
  swing: "#00FF87",
  contact: "#FFD700",
  follow_through: "#FF8A00",
};

export const PHASE_LABELS: Record<string, string> = {
  idle: "Before Swing",
  stance: "Set Up",
  load: "Load",
  launch: "Launch",
  stride: "Stride",
  swing: "Turn",
  contact: "Contact",
  follow_through: "Finish",
};

export function metricZone(key: string, value: number): "good" | "moderate" | "poor" {
  const range = METRIC_RANGES[key];
  if (!range) return "moderate";
  if (value >= range.good[0] && value <= range.good[1]) return "good";
  if (value >= range.moderate[0] && value <= range.moderate[1]) return "moderate";
  return "poor";
}

export function formatMetric(key: string, value: unknown): string {
  const range = METRIC_RANGES[key];
  if (typeof value === "number") {
    return range?.unit ? `${value.toFixed(1)}${range.unit}` : value.toFixed(1);
  }
  return String(value);
}
