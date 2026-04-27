import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { ImprovementPlan } from "@/components/ImprovementPlan";

describe("ImprovementPlan", () => {
  test("does not render repeated filler coaching text", () => {
    const html = renderToStaticMarkup(
      <ImprovementPlan
        nextSteps={[{ text: "Keep the front side closed longer.", tone: "warn" }]}
        flags={{
          front_shoulder_closed_load: false,
          finish_height: "low",
          hip_casting: false,
        } as never}
      />,
    );

    expect(html).toContain("Keep the front side closed longer.");
    expect(html).not.toContain("One clear cue at a time.");
  });
});
