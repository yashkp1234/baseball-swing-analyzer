import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { AnimatedSwingReplay } from "@/components/AnimatedSwingReplay";
import { DEFAULT_PLAYBACK_SPEED, PLAYBACK_SPEEDS } from "@/pages/SwingViewerPage";

describe("SwingViewerPage", () => {
  test("defaults playback to quarter speed with slow speeds listed first", () => {
    expect(DEFAULT_PLAYBACK_SPEED).toBe(0.25);
    expect(PLAYBACK_SPEEDS).toEqual([0.25, 0.5, 1]);
  });

  test("renders animated replay content instead of abstract-only copy", () => {
    const html = renderToStaticMarkup(
      <AnimatedSwingReplay
        currentFrame={2}
        contactFrame={5}
        frames={[
          {
            keypoints: [
              [0, 0, 0],
              [1, 1, 0],
            ],
            keypoint_names: ["nose", "left_eye"],
            skeleton: [[0, 1]],
            phase: "load",
            efficiency: 0.4,
            velocities: {},
          },
          {
            keypoints: [
              [0.5, 0.3, 0],
              [1.2, 1.1, 0],
            ],
            keypoint_names: ["nose", "left_eye"],
            skeleton: [[0, 1]],
            phase: "launch",
            efficiency: 0.5,
            velocities: {},
            bat: {
              handle: [0.2, 0.1, 0],
              barrel: [1.3, 0.7, 0],
              confidence: 0.8,
              estimate_basis: "wrist_forearm_proxy",
            },
          },
          {
            keypoints: [
              [0.7, 0.4, 0],
              [1.4, 1.3, 0],
            ],
            keypoint_names: ["nose", "left_eye"],
            skeleton: [[0, 1]],
            phase: "contact",
            efficiency: 0.7,
            velocities: {},
          },
        ]}
      />,
    );

    expect(html).toContain("Replay");
    expect(html).toContain("Bat path");
  });
});
