import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { WhatIfSimulator } from "@/components/WhatIfSimulator";

describe("WhatIfSimulator", () => {
  test("renders a client-side score projection with sliders", () => {
    const html = renderToStaticMarkup(
      <WhatIfSimulator
        metrics={{
          x_factor_at_contact: 12,
          hip_angle_at_contact: 172,
          shoulder_angle_at_contact: 154,
          spine_tilt_at_contact: 12,
          left_knee_at_contact: 34,
          right_knee_at_contact: 28,
          head_displacement_total: 52,
        }}
      />,
    );

    expect(html).toContain("What happens if you clean this up?");
    expect(html).toContain("Current score");
    expect(html).toContain("Projected score");
    expect(html).toContain("Hip-Shoulder Separation");
    expect(html).toContain("Head Stability");
    expect(html).toContain('type="range"');
  });
});
