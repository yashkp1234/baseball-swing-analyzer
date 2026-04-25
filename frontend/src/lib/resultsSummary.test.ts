import { describe, expect, test } from "vitest";
import type { CoachingLine, SwingMetrics } from "@/lib/api";
import { buildExecutiveSummary } from "@/lib/resultsSummary";

function makeMetrics(overrides: Partial<SwingMetrics> = {}): SwingMetrics {
  return {
    phase_durations: {},
    stride_plant_frame: 12,
    contact_frame: 24,
    hip_angle_at_contact: 172,
    shoulder_angle_at_contact: 156,
    x_factor_at_contact: 28,
    spine_tilt_at_contact: 12,
    left_knee_at_contact: 32,
    right_knee_at_contact: 28,
    head_displacement_total: 18,
    wrist_peak_velocity_px_s: 1880,
    wrist_peak_velocity_normalized: 0.92,
    pose_confidence_mean: 0.93,
    frames: 36,
    fps: 120,
    phase_labels: ["stance", "load", "stride", "contact"],
    flags: {
      handedness: "right",
      front_shoulder_closed_load: true,
      leg_action: "stable",
      finish_height: "high",
      hip_casting: false,
      arm_slot_at_contact: "neutral",
    },
    ...overrides,
  };
}

describe("buildExecutiveSummary", () => {
  test("turns strong baseline metrics into a high-confidence summary", () => {
    const coaching: CoachingLine[] = [
      { tone: "info", text: "Keep the barrel moving through the middle of the field." },
      { tone: "warn", text: "Stay loaded into heel plant to preserve stretch." },
    ];

    const summary = buildExecutiveSummary(makeMetrics(), coaching);

    expect(summary.score).toBeGreaterThanOrEqual(85);
    expect(summary.label).toBe("Game-ready foundation");
    expect(summary.summary).toContain("game-ready foundation");
    expect(summary.strengths.length).toBeGreaterThan(0);
    expect(summary.nextSteps).toEqual(coaching);
  });

  test("floors a poor swing score and surfaces the cleanup label", () => {
    const summary = buildExecutiveSummary(
      makeMetrics({
        hip_angle_at_contact: 132,
        shoulder_angle_at_contact: 116,
        x_factor_at_contact: 6,
        spine_tilt_at_contact: 34,
        left_knee_at_contact: 2,
        right_knee_at_contact: 74,
        head_displacement_total: 76,
        wrist_peak_velocity_normalized: 0.42,
        flags: {
          handedness: "right",
          front_shoulder_closed_load: false,
          leg_action: "stiff",
          finish_height: "low",
          hip_casting: true,
          arm_slot_at_contact: "steep",
        },
      }),
      [],
    );

    expect(summary.score).toBe(40);
    expect(summary.label).toBe("Needs cleanup");
    expect(summary.issues.length).toBeGreaterThan(0);
    expect(summary.nextSteps[0]).toEqual({
      tone: "warn",
      text: "hips leak early, which can flatten the sequence before the barrel turns loose",
    });
  });
});
