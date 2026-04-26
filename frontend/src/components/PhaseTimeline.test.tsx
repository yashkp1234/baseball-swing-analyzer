import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { PhaseTimeline } from "@/components/PhaseTimeline";

describe("PhaseTimeline", () => {
  test("renders human labels instead of raw phase keys", () => {
    const html = renderToStaticMarkup(
      <PhaseTimeline
        phaseLabels={["stance", "load", "stride", "swing", "contact", "follow_through"]}
        totalFrames={6}
        currentFrame={3}
        contactFrame={4}
        stridePlantFrame={2}
      />,
    );

    expect(html).toContain("Set Up");
    expect(html).toContain("Turn");
    expect(html).toContain("Finish");
    expect(html).not.toContain(">follow_through<");
  });
});
