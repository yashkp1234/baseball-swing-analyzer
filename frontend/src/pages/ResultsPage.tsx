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
import { artifactUrl, getJobResults, getJobStatus, type SwingMetrics } from "@/lib/api";
import { buildExecutiveSummary } from "@/lib/resultsSummary";

const DISPLAY_METRICS: { key: keyof SwingMetrics; label: string }[] = [
  { key: "x_factor_at_contact", label: "Hip-Shoulder Separation" },
  { key: "hip_angle_at_contact", label: "Hip Angle" },
  { key: "shoulder_angle_at_contact", label: "Shoulder Angle" },
  { key: "spine_tilt_at_contact", label: "Spine Tilt" },
  { key: "left_knee_at_contact", label: "L Knee Flex" },
  { key: "right_knee_at_contact", label: "R Knee Flex" },
  { key: "head_displacement_total", label: "Head Movement" },
  { key: "wrist_peak_velocity_normalized", label: "Peak Wrist Vel (norm)" },
];

export function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [currentFrame, setCurrentFrame] = useState(0);
  const [selectedSwingIndex, setSelectedSwingIndex] = useState(0);
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

  const swingSegments = resolvedMetrics.swing_segments ?? [];
  const hasMultipleSwings = swingSegments.length > 1;
  const selectedSwingNumber = selectedSwingIndex + 1;
  const videoSrc = artifactUrl(jobId, hasMultipleSwings ? `annotated_swing_${selectedSwingNumber}.mp4` : "annotated.mp4");
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

      <main className="mx-auto max-w-[1680px] px-5 py-6 space-y-8 lg:px-8">
        <section
          aria-label="Executive summary and annotated video"
          className="overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,rgba(13,18,28,0.98),rgba(22,28,38,0.94))] shadow-[0_24px_80px_rgba(0,0,0,0.28)]"
        >
          <div className="grid gap-0 xl:grid-cols-[minmax(0,1.35fr)_minmax(420px,0.95fr)]">
            <ExecutiveSummaryHero summary={executiveSummary} embedded />

            <div className="border-t border-white/8 bg-[rgba(7,10,16,0.34)] p-5 lg:p-6 xl:border-l xl:border-t-0">
              <CardTitle className="mb-2 px-1">Annotated Video</CardTitle>
              <p className="mb-4 max-w-3xl px-1 text-sm leading-6 text-[var(--color-text-dim)]">
                Review the swing clip next to the coaching summary.
              </p>
              {hasMultipleSwings ? (
                <div className="mb-4 flex flex-wrap gap-2 px-1" aria-label="Swing choices">
                  {swingSegments.map((segment, index) => (
                    <button
                      key={`${segment.start_frame}-${segment.end_frame}`}
                      type="button"
                      onClick={() => {
                        setSelectedSwingIndex(index);
                        setCurrentFrame(0);
                      }}
                      className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${
                        selectedSwingIndex === index
                          ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-[var(--color-bg)]"
                          : "border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-text)]"
                      }`}
                    >
                      Swing {index + 1}
                    </button>
                  ))}
                </div>
              ) : null}
              <VideoPlayer
                ref={videoRef}
                src={videoSrc}
                fps={resolvedMetrics.fps}
                selectedFrame={currentFrame}
                onFrameChange={setCurrentFrame}
              />

              <div className="mt-4 space-y-4">
                <Link
                  to={`/viewer/${jobId}${hasMultipleSwings ? `?swing=${selectedSwingNumber}` : ""}`}
                  className="flex items-center justify-center gap-2 rounded-[20px] border border-[var(--color-accent)]/40 bg-[var(--color-accent)]/10 px-6 py-4 text-sm font-semibold text-[var(--color-accent)] transition hover:bg-[var(--color-accent)]/18"
                >
                  <Box className="h-5 w-5" />
                  See Swing Breakdown
                </Link>
              </div>
            </div>
          </div>
        </section>

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
