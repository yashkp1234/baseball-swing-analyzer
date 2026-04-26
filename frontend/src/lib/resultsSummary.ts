import type { CoachingLine, SwingMetrics } from "@/lib/api";
import { metricZone } from "@/lib/metrics";

export interface ExecutiveSummaryModel {
  score: number;
  label: string;
  summary: string;
  strengths: string[];
  issues: string[];
  nextSteps: ExecutiveSummaryStep[];
}

type ScoreZone = "good" | "moderate" | "poor";

export interface ExecutiveSummaryStep {
  text: string;
  tone: CoachingLine["tone"];
}

const SCORED_METRICS: Array<keyof SwingMetrics> = [
  "x_factor_at_contact",
  "hip_angle_at_contact",
  "shoulder_angle_at_contact",
  "spine_tilt_at_contact",
  "left_knee_at_contact",
  "right_knee_at_contact",
  "head_displacement_total",
];

function wristVelocityZone(value: number): ScoreZone {
  if (value >= 0.8 && value <= 1.2) return "good";
  if (value >= 0.65 && value <= 1.4) return "moderate";
  return "poor";
}

function scorePoints(zone: ScoreZone): number {
  if (zone === "good") return 12;
  if (zone === "moderate") return 8;
  return 4;
}

function buildScore(metrics: SwingMetrics): number {
  const total = SCORED_METRICS.reduce((points, key) => {
    return points + scorePoints(metricZone(String(key), metrics[key] as number));
  }, 0);

  return Math.max(40, Math.min(99, total + scorePoints(wristVelocityZone(metrics.wrist_peak_velocity_normalized))));
}

function buildLabel(score: number): string {
  if (score >= 85) return "Game-ready foundation";
  if (score >= 70) return "Promising swing";
  return "Needs cleanup";
}

function pickStrengths(metrics: SwingMetrics): string[] {
  const strengths: string[] = [];

  if (!metrics.flags.hip_casting) {
    strengths.push("Rotation stays connected instead of leaking early from the pelvis.");
  }
  if (metrics.flags.front_shoulder_closed_load) {
    strengths.push("The front shoulder stays closed through load, preserving stretch into launch.");
  }
  if (metrics.head_displacement_total <= 30) {
    strengths.push("Head movement stays quiet, giving the swing a stable visual base.");
  }
  if (metrics.flags.finish_height === "high") {
    strengths.push("The finish works uphill through the zone, which supports extension.");
  }
  if (metrics.x_factor_at_contact >= 20) {
    strengths.push("Hip-shoulder separation is present at contact, which helps carry usable rotational energy.");
  }

  if (strengths.length === 0) {
    strengths.push("The swing still shows an athletic base that can be organized into a cleaner pattern.");
  }

  return strengths.slice(0, 3);
}

function pickIssues(metrics: SwingMetrics): string[] {
  const issues: string[] = [];

  if (metrics.flags.hip_casting) {
    issues.push("The hips leak early, which can flatten the sequence before the barrel turns loose.");
  }
  if (!metrics.flags.front_shoulder_closed_load) {
    issues.push("The lead shoulder opens too soon and gives away stretch before contact.");
  }
  if (metrics.flags.finish_height !== "high") {
    issues.push("The finish cuts off extension, limiting how long the barrel works through contact.");
  }
  if (metrics.x_factor_at_contact < 15) {
    issues.push("Hip-shoulder separation is shallow, so the swing stores less rotational energy.");
  }
  if (metrics.head_displacement_total > 45) {
    issues.push("Head movement drifts too much, making contact harder to repeat.");
  }

  if (issues.length === 0) {
    issues.push("The main opportunity is sharpening consistency so the better moves show up swing after swing.");
  }

  return issues.slice(0, 3);
}

function pickNextSteps(
  coaching: CoachingLine[] | null | undefined,
  issues: string[],
): ExecutiveSummaryStep[] {
  const coachingLines = (coaching ?? [])
    .map((line) => ({ text: line.text.trim(), tone: line.tone }))
    .filter((line) => line.text);
  if (coachingLines.length > 0) {
    return coachingLines.slice(0, 4);
  }

  return issues
    .map((issue) => ({
      text: issue.replace(/^The /, "").replace(/\.$/, ""),
      tone: "warn" as const,
    }))
    .slice(0, 3);
}

function buildSummary(label: string, score: number, strengths: string[], nextSteps: ExecutiveSummaryStep[]): string {
  const opener =
    score >= 85
      ? `This swing shows a ${label.toLowerCase()}.`
      : score >= 70
        ? "This swing has a solid foundation with room to sharpen."
        : "This swing needs cleaner movement before the power can play consistently.";

  return [opener, strengths[0], nextSteps[0] ? `Next priority: ${nextSteps[0].text}` : null].filter(Boolean).join(" ");
}

export function buildExecutiveSummary(
  metrics: SwingMetrics,
  coaching: CoachingLine[] | null | undefined,
): ExecutiveSummaryModel {
  const score = buildScore(metrics);
  const label = buildLabel(score);
  const strengths = pickStrengths(metrics);
  const issues = pickIssues(metrics);
  const nextSteps = pickNextSteps(coaching, issues);

  return {
    score,
    label,
    summary: buildSummary(label, score, strengths, nextSteps),
    strengths,
    issues,
    nextSteps,
  };
}
