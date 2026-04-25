import { useQuery } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";
import type { AnalysisSummary, JobResults, JobStatus, SwingMetrics } from "@/lib/api";
import { ResultsPage } from "@/pages/ResultsPage";

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(),
}));

const mockUseQuery = vi.mocked(useQuery);

const metrics: SwingMetrics = {
  phase_durations: { load: 120, launch: 80, contact: 40 },
  stride_plant_frame: 22,
  contact_frame: 31,
  hip_angle_at_contact: 38,
  shoulder_angle_at_contact: 20,
  x_factor_at_contact: 18,
  spine_tilt_at_contact: 16,
  left_knee_at_contact: 42,
  right_knee_at_contact: 28,
  head_displacement_total: 24,
  wrist_peak_velocity_px_s: 920,
  wrist_peak_velocity_normalized: 0.92,
  pose_confidence_mean: 0.93,
  frames: 72,
  fps: 240,
  phase_labels: ["load", "launch", "contact"],
  flags: {
    handedness: "right",
    front_shoulder_closed_load: true,
    leg_action: "stable",
    finish_height: "high",
    hip_casting: false,
    arm_slot_at_contact: "connected",
  },
};

const analysis: AnalysisSummary = {
  pose_device: "cuda",
  source_frames: 180,
  source_fps: 240,
  sampled_frames: 90,
  effective_analysis_fps: 120,
  sampling_mode: "adaptive",
  analysis_duration_ms: 1650,
  pose_inference_duration_ms: 920,
};

const status: JobStatus = {
  job_id: "job-123",
  status: "completed",
  progress: 100,
  current_step: null,
  error_message: null,
};

const results: JobResults = {
  job_id: "job-123",
  status: "completed",
  metrics,
  analysis,
  coaching: [{ tone: "info", text: "Stay closed longer into launch." }],
  frames_3d_url: "/api/jobs/job-123/artifacts/frames_3d.json",
};

describe("ResultsPage", () => {
  beforeEach(() => {
    mockUseQuery.mockReset();
  });

  test("groups the executive summary hero and annotated video into one overview surface", () => {
    mockUseQuery.mockReturnValueOnce({ data: status } as never).mockReturnValueOnce({ data: results } as never);

    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={["/results/job-123"]}>
        <Routes>
          <Route path="/results/:jobId" element={<ResultsPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(html).toContain('aria-label="Executive summary and annotated video"');
    expect(html).toContain("Executive Summary");
    expect(html).toContain("Annotated Video");
  });

  test("folds coaching and flags into the narrative flow and demotes the raw metrics section", () => {
    mockUseQuery.mockReturnValueOnce({ data: status } as never).mockReturnValueOnce({ data: results } as never);

    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={["/results/job-123"]}>
        <Routes>
          <Route path="/results/:jobId" element={<ResultsPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(html).toContain("What&#x27;s working");
    expect(html).toContain("What&#x27;s costing performance");
    expect(html).toContain("What to improve next");
    expect(html).toContain("Stay closed longer into launch.");
    expect(html).not.toContain("Qualitative Flags");
    expect(html).not.toContain("Coaching Report");
    expect(html).toContain("Supporting metrics");

    const storyStart = html.indexOf("What&#x27;s working");
    const metricsStart = html.indexOf("Supporting metrics");

    expect(storyStart).toBeGreaterThan(-1);
    expect(metricsStart).toBeGreaterThan(-1);
    expect(storyStart).toBeLessThan(metricsStart);
  });
});
