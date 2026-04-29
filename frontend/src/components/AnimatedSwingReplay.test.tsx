import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { AnimatedSwingReplay } from "@/components/AnimatedSwingReplay";

describe("AnimatedSwingReplay", () => {
  test("renders estimated contact and exit-trajectory cues instead of exact tracking claims", () => {
    const html = renderToStaticMarkup(
      <AnimatedSwingReplay
        currentFrame={2}
        contactFrame={1}
        frames={[
          {
            keypoints: [[0, 0, 0], [1, 1, 0]],
            keypoint_names: ["nose", "left_eye"],
            skeleton: [[0, 1]],
            phase: "load",
            efficiency: 0.4,
            velocities: {},
            bat: { handle: [0, 0, 0], barrel: [0.8, 0.2, 0], confidence: 0.8, estimate_basis: "wrist_forearm_proxy" },
          },
          {
            keypoints: [[0.1, 0.1, 0], [1.1, 1, 0]],
            keypoint_names: ["nose", "left_eye"],
            skeleton: [[0, 1]],
            phase: "contact",
            efficiency: 0.5,
            velocities: {},
            bat: { handle: [0.1, 0.1, 0], barrel: [1.0, 0.3, 0], confidence: 0.8, estimate_basis: "wrist_forearm_proxy" },
          },
          {
            keypoints: [[0.2, 0.2, 0], [1.2, 1, 0]],
            keypoint_names: ["nose", "left_eye"],
            skeleton: [[0, 1]],
            phase: "follow_through",
            efficiency: 0.6,
            velocities: {},
            bat: { handle: [0.2, 0.2, 0], barrel: [1.2, 0.5, 0], confidence: 0.8, estimate_basis: "wrist_forearm_proxy" },
          },
        ]}
      />,
    );

    expect(html).toContain("Interpretive replay");
    expect(html).toContain("Estimated contact");
    expect(html).toContain("Estimated exit path");
    expect(html).not.toContain("measured bat-tracking");
  });
});
