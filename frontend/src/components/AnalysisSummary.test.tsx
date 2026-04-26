import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { AnalysisSummary } from "@/components/AnalysisSummary";

describe("AnalysisSummary", () => {
  test("renders analysis details as lower-priority diagnostics copy", () => {
    const html = renderToStaticMarkup(
      <AnalysisSummary
        analysis={{
          pose_device: "cuda",
          source_frames: 180,
          source_fps: 240,
          sampled_frames: 90,
          effective_analysis_fps: 120,
          sampling_mode: "adaptive",
          analysis_duration_ms: 1650,
          pose_inference_duration_ms: 920,
        }}
      />,
    );

    expect(html).toContain("Analysis details");
    expect(html).toContain("Processing transparency for advanced review.");
    expect(html).not.toContain("Analysis Summary");
    expect(html).toContain("Device");
    expect(html).toContain("Runtime");
  });
});
