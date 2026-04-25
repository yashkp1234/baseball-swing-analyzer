import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { type AnalysisResponse, type SwingMetrics, artifactUrl } from "@/lib/api";
import { Card, CardTitle } from "@/components/Card";
import { MetricCard } from "@/components/MetricCard";
import { PhaseTimeline } from "@/components/PhaseTimeline";
import { FlagsPanel } from "@/components/FlagsPanel";
import { CoachingReport } from "@/components/CoachingReport";
import { VideoPlayer } from "@/components/VideoPlayer";
import { ArrowLeft, Box } from "lucide-react";

const DISPLAY_METRICS: { key: keyof SwingMetrics; label: string }[] = [
  { key: "x_factor_at_contact", label: "X-Factor" },
  { key: "hip_angle_at_contact", label: "Hip Angle" },
  { key: "shoulder_angle_at_contact", label: "Shoulder Angle" },
  { key: "spine_tilt_at_contact", label: "Spine Tilt" },
  { key: "left_knee_at_contact", label: "L Knee Flex" },
  { key: "right_knee_at_contact", label: "R Knee Flex" },
  { key: "head_displacement_total", label: "Head Displace" },
  { key: "wrist_peak_velocity_px_s", label: "Peak Wrist Vel" },
];

export function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [data, setData] = useState<AnalysisResponse | null>(null);

  useEffect(() => {
    if (!jobId) return;
    const cached = sessionStorage.getItem(`result_${jobId}`);
    if (cached) {
      setData(JSON.parse(cached));
    }
  }, [jobId]);

  if (!data || data.status === "failed") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <p className="text-[var(--color-red)] font-medium">
            {data?.error || "No results found for this analysis."}
          </p>
          <Link to="/" className="mt-4 inline-block text-[var(--color-accent)] text-sm hover:underline">
            Upload a new video
          </Link>
        </Card>
      </div>
    );
  }

  const m = data.metrics;
  if (!m) return <div className="min-h-screen flex items-center justify-center text-[var(--color-text-dim)]">No metrics data.</div>;

  const videoSrc = artifactUrl(jobId!, "annotated.mp4");

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <header className="border-b border-[var(--color-border)] px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-[var(--color-text-dim)] hover:text-[var(--color-text)] transition-colors">
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">New Analysis</span>
        </Link>
        <h1 className="text-lg font-semibold">
          Swing<span className="text-[var(--color-accent)]">Metrics</span>
        </h1>
        <div className="w-24" />
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        <Card>
          <CardTitle>Phase Timeline</CardTitle>
          <PhaseTimeline phaseLabels={m.phase_labels} />
          <div className="mt-2 flex gap-4 text-xs text-[var(--color-text-dim)]">
            <span>Stride plant: frame {m.stride_plant_frame ?? "—"}</span>
            <span>Contact: frame {m.contact_frame}</span>
            <span>Total: {m.frames} frames @ {m.fps.toFixed(1)} fps</span>
          </div>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardTitle>Annotated Video</CardTitle>
              <VideoPlayer src={videoSrc} />
            </Card>

            <Card>
              <CardTitle>Qualitative Flags</CardTitle>
              <FlagsPanel flags={m.flags} />
            </Card>

            <CoachingReport html={data.coaching_html} />
          </div>

          <div className="space-y-3">
            <CardTitle className="px-1">Key Metrics</CardTitle>
            <div className="grid grid-cols-1 gap-3">
              {DISPLAY_METRICS.map(({ key, label }) => {
                const val = m[key];
                return <MetricCard key={key} label={label} value={typeof val === "number" ? val : String(val)} metricKey={key} />;
              })}
            </div>

            <Card className="mt-4">
              <CardTitle>Phase Durations</CardTitle>
              <div className="space-y-1">
                {Object.entries(m.phase_durations).map(([phase, count]) => (
                  <div key={phase} className="flex justify-between text-sm">
                    <span className="text-[var(--color-text-dim)]">{phase}</span>
                    <span className="font-mono text-[var(--color-text)]">{count} frames</span>
                  </div>
                ))}
              </div>
            </Card>

            <Link
              to={`/viewer/${jobId}`}
              state={{ data }}
              className="mt-4 flex items-center justify-center gap-2 rounded-xl border-2 border-[var(--color-accent)] bg-[var(--color-accent)]/10 px-6 py-4 text-[var(--color-accent)] font-semibold hover:bg-[var(--color-accent)]/20 transition-all"
            >
              <Box className="h-5 w-5" />
              Launch 3D Swing Viewer
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}