import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { getJobStatus, getJobResults, artifactUrl, type SportProfile, type SwingMetrics } from "@/lib/api";
import { Card, CardTitle } from "@/components/Card";
import { MetricCard } from "@/components/MetricCard";
import { PhaseTimeline } from "@/components/PhaseTimeline";
import { FlagsPanel } from "@/components/FlagsPanel";
import { CoachingReport } from "@/components/CoachingReport";
import { VideoPlayer } from "@/components/VideoPlayer";
import { ProcessingStatus } from "@/components/ProcessingStatus";
import { AnalysisSummary } from "@/components/AnalysisSummary";
import { ArrowLeft, Box } from "lucide-react";

const DISPLAY_METRICS: { key: keyof SwingMetrics; label: string }[] = [
  { key: "x_factor_at_contact", label: "X-Factor" },
  { key: "hip_angle_at_contact", label: "Hip Angle" },
  { key: "shoulder_angle_at_contact", label: "Shoulder Angle" },
  { key: "spine_tilt_at_contact", label: "Spine Tilt" },
  { key: "left_knee_at_contact", label: "L Knee Flex" },
  { key: "right_knee_at_contact", label: "R Knee Flex" },
  { key: "head_displacement_total", label: "Head Displace" },
  { key: "wrist_peak_velocity_normalized", label: "Peak Wrist Vel (norm)" },
];

function sportLabel(profile: SportProfile | null | undefined): string {
  if (!profile) return "Not confidently detected";
  if (profile.label === "baseball") return "Baseball";
  if (profile.label === "softball") return "Softball";
  return "Not confidently detected";
}

function sportNote(profile: SportProfile | null | undefined): string {
  if (!profile || profile.label === "unknown") {
    return "Using shared hitting guidance because the clip did not contain a strong baseball or softball signal.";
  }
  return `Using ${profile.label}-aware interpretation where wording and thresholds differ.`;
}

export function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();

  const statusQuery = useQuery({
    queryKey: ["status", jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "completed" || s === "failed" ? false : 1500;
    },
  });

  const isReady = statusQuery.data?.status === "completed" || statusQuery.data?.status === "failed";

  const resultsQuery = useQuery({
    queryKey: ["results", jobId],
    queryFn: () => getJobResults(jobId!),
    enabled: !!jobId && isReady,
  });

  if (!jobId) return null;

  if (!isReady) {
    return <ProcessingStatus status={statusQuery.data} />;
  }

  if (statusQuery.data?.status === "failed" || resultsQuery.data?.status === "failed") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <p className="text-[var(--color-red)] font-medium">
            {statusQuery.data?.error_message || "Analysis failed."}
          </p>
          <Link to="/" className="mt-4 inline-block text-[var(--color-accent)] text-sm hover:underline">
            Try another video
          </Link>
        </Card>
      </div>
    );
  }

  const m = resultsQuery.data?.metrics;
  if (!m) return <div className="min-h-screen flex items-center justify-center">Loading…</div>;

  const videoSrc = artifactUrl(jobId, "annotated.mp4");
  const sportProfile = resultsQuery.data?.sport_profile;

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <header className="border-b border-[var(--color-border)] px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-[var(--color-text-dim)] hover:text-[var(--color-text)]">
          <ArrowLeft className="h-4 w-4" /><span className="text-sm">New Analysis</span>
        </Link>
        <h1 className="text-lg font-semibold">Swing<span className="text-[var(--color-accent)]">Metrics</span></h1>
        <div className="w-24" />
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        <AnalysisSummary analysis={resultsQuery.data?.analysis} />

        <Card>
          <CardTitle>Detected Sport</CardTitle>
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-lg font-semibold">{sportLabel(sportProfile)}</p>
              <p className="mt-1 text-sm text-[var(--color-text-dim)]">{sportNote(sportProfile)}</p>
            </div>
            {sportProfile ? (
              <div className="text-right text-xs text-[var(--color-text-dim)]">
                <div>Confidence {(sportProfile.confidence * 100).toFixed(0)}%</div>
                <div>Context {(sportProfile.context_confidence * 100).toFixed(0)}%</div>
                <div>Mechanics {(sportProfile.mechanics_confidence * 100).toFixed(0)}%</div>
              </div>
            ) : null}
          </div>
        </Card>

        <Card>
          <CardTitle>Phase Timeline</CardTitle>
          <PhaseTimeline phaseLabels={m.phase_labels} />
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-[var(--color-text-dim)]">
            <span>Stride plant: frame {m.stride_plant_frame ?? "—"}</span>
            <span>Contact: frame {m.contact_frame}</span>
            <span>Total: {m.frames} frames @ {m.fps.toFixed(1)} fps</span>
            <span>Pose confidence: {(m.pose_confidence_mean * 100).toFixed(0)}%</span>
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
            <CoachingReport lines={resultsQuery.data?.coaching ?? []} />
          </div>

          <div className="space-y-3">
            <CardTitle className="px-1">Key Metrics</CardTitle>
            <div className="grid grid-cols-1 gap-3">
              {DISPLAY_METRICS.map(({ key, label }) => {
                const val = m[key];
                return <MetricCard key={key as string} label={label} value={typeof val === "number" ? val : String(val)} metricKey={key as string} />;
              })}
            </div>
            <Link
              to={`/viewer/${jobId}`}
              className="mt-4 flex items-center justify-center gap-2 rounded-xl border-2 border-[var(--color-accent)] bg-[var(--color-accent)]/10 px-6 py-4 text-[var(--color-accent)] font-semibold hover:bg-[var(--color-accent)]/20"
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
