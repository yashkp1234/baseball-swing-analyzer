import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { FixTogglePanel } from "@/components/FixTogglePanel";

describe("FixTogglePanel", () => {
  test("renders a toggle and estimate changes without sliders", () => {
    const html = renderToStaticMarkup(
      <FixTogglePanel
        enabled={false}
        pending={false}
        baseline={{ estimate_basis: "pose_proxy", exit_velocity_mph: 70, exit_velocity_mph_low: 65, exit_velocity_mph_high: 75, carry_distance_ft: 210, carry_distance_ft_low: 190, carry_distance_ft_high: 230, score: 64 }}
        projection={{ estimate_basis: "pose_proxy", exit_velocity_mph: 76, exit_velocity_mph_low: 71, exit_velocity_mph_high: 81, carry_distance_ft: 238, carry_distance_ft_low: 218, carry_distance_ft_high: 258, score: 72 }}
        fix={{ id: "lower_half_timing", label: "Fix lower-half timing", coach_text: "Keep the stride controlled." }}
        onToggle={() => undefined}
      />,
    );

    expect(html).toContain("Fix lower-half timing");
    expect(html).toContain("64");
    expect(html).toContain("70 mph");
    expect(html).not.toMatch(/slider|range/i);
  });
});
