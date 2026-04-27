import { useQuery } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { PhaseTimeline } from "@/components/PhaseTimeline";
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
  sport_profile: null,
  coaching: [{ tone: "info", text: "Stay closed longer into launch." }],
  frames_3d_url: "/api/jobs/job-123/artifacts/frames_3d.json",
  analysis_version: "2026-04-swing-redesign-v1",
  is_current_analysis: true,
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
    expect(html).toContain("Promising swing");
    expect(html).toContain("Annotated Video");
    expect(html).toContain("See Swing Breakdown");
    expect(html).toContain("Plain-English terms");
    expect(html).toContain("Hip-shoulder separation (X-factor)");
    expect(html).not.toMatch(/Detected Sport|Context|Mechanics|not confidently detected/i);
  });

  test("keeps the story sections primary and moves diagnostics into a secondary details band", () => {
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
    expect(html).toContain("Details and diagnostics");
    expect(html).toContain("Analysis details");
    expect(html).toContain("Phase Timeline");
    expect(html).toContain("Supporting metrics");

    const storyStart = html.indexOf("What&#x27;s working");
    const nextActionsStart = html.indexOf("What to improve next");
    const detailsStart = html.indexOf("Details and diagnostics");
    const timelineStart = html.indexOf("Phase Timeline");
    const metricsStart = html.indexOf("Supporting metrics");

    expect(storyStart).toBeGreaterThan(-1);
    expect(nextActionsStart).toBeGreaterThan(-1);
    expect(detailsStart).toBeGreaterThan(-1);
    expect(timelineStart).toBeGreaterThan(-1);
    expect(metricsStart).toBeGreaterThan(-1);
    expect(storyStart).toBeLessThan(nextActionsStart);
    expect(nextActionsStart).toBeLessThan(detailsStart);
    expect(detailsStart).toBeLessThan(timelineStart);
    expect(timelineStart).toBeLessThan(metricsStart);
  });

  test("renders an interactive timeline with marker callouts inside diagnostics", () => {
    mockUseQuery.mockReturnValueOnce({ data: status } as never).mockReturnValueOnce({ data: results } as never);

    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={["/results/job-123"]}>
        <Routes>
          <Route path="/results/:jobId" element={<ResultsPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(html).toContain("Select a phase to jump the annotated video.");
    expect(html).toContain('type="button"');
    expect(html).toContain("Stride plant");
    expect(html).toContain("Contact");
  });

  test("shows compact swing choices when multiple segments are available", () => {
    mockUseQuery.mockReturnValueOnce({ data: status } as never).mockReturnValueOnce({
      data: {
        ...results,
        metrics: {
          ...metrics,
          swing_segments: [
            { start_frame: 0, end_frame: 30, contact_frame: 20, duration_s: 1, confidence: 0.8 },
            { start_frame: 45, end_frame: 75, contact_frame: 62, duration_s: 1, confidence: 0.9 },
          ],
        },
      },
    } as never);

    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={["/results/job-123"]}>
        <Routes>
          <Route path="/results/:jobId" element={<ResultsPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(html).toContain("Swing 1");
    expect(html).toContain("Swing 2");
  });

  test("surfaces stale or low-confidence analysis warnings above the summary", () => {
    mockUseQuery.mockReturnValueOnce({ data: status } as never).mockReturnValueOnce({
      data: {
        ...results,
        is_current_analysis: false,
        analysis_version: "2026-03-legacy",
        metrics: {
          ...metrics,
          measurement_reliability: "low",
        },
      },
    } as never);

    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={["/results/job-123"]}>
        <Routes>
          <Route path="/results/:jobId" element={<ResultsPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(html).toContain("older analysis pass");
    expect(html).toContain("2026-03-legacy");
    expect(html).toContain("Pose confidence is low on this clip");
  });
});

describe("PhaseTimeline", () => {
  test("marks the selected segment and exposes phase guidance for focus and hover", () => {
    const html = renderToStaticMarkup(
      <PhaseTimeline
        phaseLabels={["load", "load", "stride", "stride", "contact"]}
        currentFrame={3}
        contactFrame={4}
        stridePlantFrame={2}
      />,
    );

    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain("Gathering move that stores tension before the swing starts forward.");
    expect(html).toContain("Move into foot strike so the body can brace before rotation.");
    expect(html).toContain("Barrel enters the hit window and meets the ball.");
  });
});
