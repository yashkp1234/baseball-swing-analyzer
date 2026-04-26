import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { ExecutiveSummaryHero } from "@/components/ExecutiveSummaryHero";

describe("ExecutiveSummaryHero", () => {
  test("renders only player-facing coaching language", () => {
    const html = renderToStaticMarkup(
      <ExecutiveSummaryHero
        summary={{
          score: 64,
          label: "Needs cleanup",
          summary: "This swing needs cleaner movement before the power can play consistently.",
          strengths: ["Rotation stays connected instead of leaking early from the pelvis."],
          issues: ["Foot plant is early."],
          nextSteps: [{ tone: "warn", text: "Try a softer, controlled toe-tap load." }],
        }}
      />,
    );

    expect(html).toContain("64");
    expect(html).toContain("Needs cleanup");
    expect(html).toContain("Try a softer, controlled toe-tap load.");
    expect(html).not.toMatch(/Score Signal|Evidence Layer|Immediate Read|proof surface|diagnostics/i);
  });
});
