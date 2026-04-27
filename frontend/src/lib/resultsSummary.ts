import type { CoachingLine, SwingMetrics } from "@/lib/api";
import { metricZone } from "@/lib/metrics";

export interface ExecutiveSummaryModel {
  score: number;
  label: string;
  summary: string;
  strengths: string[];
  issues: string[];
  nextSteps: ExecutiveSummaryStep[];
  terms: SummaryTerm[];
}

type ScoreZone = "good" | "moderate" | "poor";

export interface ExecutiveSummaryStep {
  text: string;
  tone: CoachingLine["tone"];
  why?: string;
  drill?: string;
}

export interface SummaryTerm {
  term: string;
  definition: string;
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
    strengths.push("Your hips and shoulders are turning in sequence instead of the hips spinning open too early.");
  }
  if (metrics.flags.front_shoulder_closed_load) {
    strengths.push("Your front shoulder stays closed during the load, which gives you more room to turn into contact.");
  }
  if (metrics.head_displacement_total <= 30) {
    strengths.push("Your head stays fairly steady, which makes the ball easier to track.");
  }
  if (metrics.flags.finish_height === "high") {
    strengths.push("Your finish stays high through contact, which helps the bat keep moving through the ball.");
  }
  if (metrics.x_factor_at_contact >= 20) {
    strengths.push("You create useful hip-shoulder separation at contact, so the torso is storing some turn.");
  }

  if (strengths.length === 0) {
    strengths.push("The swing still shows an athletic base that can be organized into a cleaner pattern.");
  }

  return strengths.slice(0, 3);
}

function pickIssues(metrics: SwingMetrics): string[] {
  const issues: string[] = [];

  if (metrics.flags.hip_casting) {
    issues.push("Your hips are opening too early, so power starts leaking before the bat gets moving.");
  }
  if (!metrics.flags.front_shoulder_closed_load) {
    issues.push("Your front shoulder opens too soon, so you lose stored rotation before contact.");
  }
  if (metrics.flags.finish_height !== "high") {
    issues.push("The finish gets cut off, so the bat stops working through contact too early.");
  }
  if (metrics.x_factor_at_contact < 15) {
    issues.push("There is not much hip-shoulder separation at contact, so the torso is not storing much turn.");
  }
  if (metrics.head_displacement_total > 45) {
    issues.push("Your head moves too much from load to contact, which makes timing harder to repeat.");
  }

  if (issues.length === 0) {
    issues.push("The main opportunity is sharpening consistency so the better moves show up swing after swing.");
  }

  return issues.slice(0, 3);
}

function rewriteCoachingLine(text: string): string {
  const trimmed = text.trim();
  const rewrites: Array<[RegExp, string]> = [
    [
      /^X-factor is very large.+$/i,
      "Hip-shoulder separation (X-factor) is on the high side. In plain English: your upper and lower body may be getting too far apart, which can leave the bat late to contact.",
    ],
    [
      /^X-factor is too small.+$/i,
      "Hip-shoulder separation (X-factor) is on the low side. Let the hips start the turn before the shoulders and hands follow.",
    ],
    [
      /^Foot plant is early.+$/i,
      "Your front foot is landing early. Slow the stride down so you can stay gathered before you turn.",
    ],
    [
      /^Foot plant is late.+$/i,
      "Your front foot is landing late. Get the stride down a little sooner so the lower half is braced before the swing.",
    ],
    [
      /^Head is moving a lot.+$/i,
      "Your head is moving too much from load to contact. Staying more centered should make timing easier.",
    ],
    [
      /^Front shoulder is opening early.+$/i,
      "Your front shoulder is opening early. Keep it closed a beat longer so the torso stays loaded into launch.",
    ],
    [
      /^Hips are casting early.+$/i,
      "Your hips are spinning early. Let the stride foot get down before the hips really fire.",
    ],
    [
      /^Low finish detected.+$/i,
      "Your finish stays low. Let the bat keep moving through contact instead of cutting off right after impact.",
    ],
  ];

  for (const [pattern, replacement] of rewrites) {
    if (pattern.test(trimmed)) return replacement;
  }
  return trimmed.replaceAll("lead shoulder", "front shoulder");
}

function coachingTopic(text: string): string {
  const normalized = text.toLowerCase();
  if (normalized.includes("x-factor") || normalized.includes("hip-shoulder separation")) return "separation";
  if (normalized.includes("front foot") || normalized.includes("foot plant") || normalized.includes("stride")) return "stride";
  if (normalized.includes("head")) return "head";
  if (normalized.includes("front shoulder")) return "front-shoulder";
  if (normalized.includes("finish")) return "finish";
  if (normalized.includes("hips")) return "hips";
  return normalized;
}

function coachingWhy(text: string): string | undefined {
  const topic = coachingTopic(text);
  if (topic === "separation") {
    return "This helps the barrel arrive on time instead of leaving the upper body stuck behind the turn.";
  }
  if (topic === "stride") {
    return "A calmer landing gives the lower half something stable to turn against.";
  }
  if (topic === "head") {
    return "A steadier head usually makes the ball easier to track and timing easier to repeat.";
  }
  if (topic === "front-shoulder") {
    return "Keeping the front side closed a beat longer preserves stretch for the swing forward.";
  }
  if (topic === "finish") {
    return "Longer extension keeps the barrel in the hit zone instead of stopping at contact.";
  }
  if (topic === "hips") {
    return "Better sequencing keeps power from leaking before the hands and barrel can use it.";
  }
  return undefined;
}

function pickNextSteps(
  coaching: CoachingLine[] | null | undefined,
  issues: string[],
): ExecutiveSummaryStep[] {
  const seenTopics = new Set<string>();
  const coachingLines = (coaching ?? [])
    .map((line) => {
      const text = rewriteCoachingLine(line.text);
      return { text, tone: line.tone, why: line.why ?? coachingWhy(text), drill: line.drill };
    })
    .filter((line) => line.text);
  if (coachingLines.length > 0) {
    return coachingLines.filter((line) => {
      const topic = coachingTopic(line.text);
      if (seenTopics.has(topic)) return false;
      seenTopics.add(topic);
      return true;
    }).slice(0, 4);
  }

  return issues
    .map((issue) => {
      const text = issue.replace(/^The /, "").replace(/\.$/, "");
      return {
        text,
        tone: "warn" as const,
        why: coachingWhy(text),
        drill: undefined,
      };
    })
    .slice(0, 3);
}

function buildSummary(label: string, score: number, strengths: string[], nextSteps: ExecutiveSummaryStep[]): string {
  const opener =
    score >= 85
      ? `This swing shows a ${label.toLowerCase()}.`
      : score >= 70
        ? "This swing has a solid foundation with room to sharpen."
        : "This swing needs cleaner movement before the power can play consistently.";

  return [opener, strengths[0], nextSteps[0]?.text].filter(Boolean).join(" ");
}

function collectTerms(metrics: SwingMetrics, nextSteps: ExecutiveSummaryStep[]): SummaryTerm[] {
  const terms: SummaryTerm[] = [];
  const combinedText = nextSteps.map((step) => step.text).join(" ");
  if (metrics.x_factor_at_contact !== undefined || /x-factor|hip-shoulder separation/i.test(combinedText)) {
    terms.push({
      term: "Hip-shoulder separation (X-factor)",
      definition: "The difference between how far the hips and shoulders have turned at contact.",
    });
  }
  if (/load/i.test(combinedText)) {
    terms.push({
      term: "Load",
      definition: "The gather before the swing starts forward.",
    });
  }
  if (/contact/i.test(combinedText)) {
    terms.push({
      term: "Contact",
      definition: "The moment the bat reaches the ball.",
    });
  }
  return terms.slice(0, 3);
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
    terms: collectTerms(metrics, nextSteps),
  };
}
