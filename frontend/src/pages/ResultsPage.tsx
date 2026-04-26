import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Box } from "lucide-react";
import { Card, CardTitle } from "@/components/Card";
import { DetailsDiagnostics } from "@/components/DetailsDiagnostics";
import { ExecutiveSummaryHero } from "@/components/ExecutiveSummaryHero";
import { ImprovementPlan } from "@/components/ImprovementPlan";
import { ProcessingStatus } from "@/components/ProcessingStatus";
import { SwingTakeaways } from "@/components/SwingTakeaways";
import { VideoPlayer, type VideoPlayerHandle } from "@/components/VideoPlayer";
import { artifactUrl, getJobResults, getJobStatus, type SportProfile, type SwingMetrics } from "@/lib/api";
import { buildExecutiveSummary } from "@/lib/resultsSummary";

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
  const [currentFrame, setCurrentFrame] = useState(0);
  const videoRef = useRef<VideoPlayerHandle>(null);

  const statusQuery = useQuery({
    queryKey: ["status", jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1500;
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

  const metrics = resultsQuery.data?.metrics;
  if (!metrics) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  const resolvedMetrics = metrics;

  const videoSrc = artifactUrl(jobId, "annotated.mp4");
  const sportProfile = resultsQuery.data?.sport_profile;
  const executiveSummary = buildExecutiveSummary(resolvedMetrics, resultsQuery.data?.coaching);

  function handleFrameSelect(frame: number) {
    setCurrentFrame(frame);
    videoRef.current?.seekToSeconds(frame / resolvedMetrics.fps);
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <header className="border-b border-[var(--color-border)] px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-[var(--color-text-dim)] hover:text-[var(--color-text)]">
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">New Analysis</span>
        </Link>
        <h1 className="text-lg font-semibold">
          Swing<span className="text-[var(--color-accent)]">Metrics</span>
        </h1>
        <div className="w-24" />
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-8">
        <section
          aria-label="Executive summary and annotated video"
          className="overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,rgba(13,18,28,0.98),rgba(22,28,38,0.94))] shadow-[0_24px_80px_rgba(0,0,0,0.28)]"
        >
          <div className="grid gap-0 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
            <ExecutiveSummaryHero summary={executiveSummary} embedded />

            <div className="border-t border-white/8 bg-[rgba(7,10,16,0.34)] p-4 lg:p-5 xl:border-l xl:border-t-0">
              <CardTitle className="mb-2 px-1">Annotated Video</CardTitle>
              <p className="mb-4 max-w-3xl px-1 text-sm leading-6 text-[var(--color-text-dim)]">
                This is the evidence layer for the report. Use it to confirm the written summary against the actual swing.
              </p>
              <VideoPlayer
                ref={videoRef}
                src={videoSrc}
                fps={resolvedMetrics.fps}
                selectedFrame={currentFrame}
                onFrameChange={setCurrentFrame}
              />

              <div className="mt-4 space-y-4">
                <Link
                  to={`/viewer/${jobId}`}
                  className="flex items-center justify-center gap-2 rounded-[20px] border border-[var(--color-accent)]/40 bg-[var(--color-accent)]/10 px-6 py-4 text-sm font-semibold text-[var(--color-accent)] transition hover:bg-[var(--color-accent)]/18"
                >
                  <Box className="h-5 w-5" />
                  Launch 3D Swing Viewer
                </Link>
              </div>
            </div>
          </div>
        </section>

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

        <SwingTakeaways strengths={executiveSummary.strengths} issues={executiveSummary.issues} />

        <ImprovementPlan
          nextSteps={executiveSummary.nextSteps}
          flags={resolvedMetrics.flags}
        />

        <DetailsDiagnostics
          analysis={resultsQuery.data?.analysis}
          metrics={resolvedMetrics}
          metricDefinitions={DISPLAY_METRICS}
          currentFrame={currentFrame}
          onFrameSelect={handleFrameSelect}
        />
      </main>
    </div>
  );
}
