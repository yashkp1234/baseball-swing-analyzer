import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Box } from "lucide-react";
import { AnimatedSwingReplay } from "@/components/AnimatedSwingReplay";
import { Card, CardTitle } from "@/components/Card";
import { DetailsDiagnostics } from "@/components/DetailsDiagnostics";
import { ExecutiveSummaryHero } from "@/components/ExecutiveSummaryHero";
import { PhaseConfidenceBanner } from "@/components/PhaseConfidenceBanner";
import { ProcessingStatus } from "@/components/ProcessingStatus";
import { SwingTakeaways } from "@/components/SwingTakeaways";
import { VideoPlayer, type VideoPlayerHandle } from "@/components/VideoPlayer";
import { artifactUrl, getFrames3D, getJobResults, getJobStatus, type Swing3DData, type SwingMetrics } from "@/lib/api";
import { createDemoResults, createDemoStatus, createDemoSwingData } from "@/lib/demoResults";
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
  const isDemo = jobId === "demo";
  const [currentFrame, setCurrentFrame] = useState(0);
  const [selectedSwingIndex, setSelectedSwingIndex] = useState(0);
  const [viewerData, setViewerData] = useState<Swing3DData | null>(() => (isDemo ? createDemoSwingData() : null));
  const videoRef = useRef<VideoPlayerHandle>(null);

  const statusQuery = useQuery({
    queryKey: ["status", jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId && !isDemo,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1500;
    },
  });

  const statusData = isDemo ? createDemoStatus() : statusQuery?.data;
  const isReady = isDemo || statusData?.status === "completed" || statusData?.status === "failed";

  const resultsQuery = useQuery({
    queryKey: ["results", jobId],
    queryFn: () => getJobResults(jobId!),
    enabled: !!jobId && isReady && !isDemo,
  });
  const resultsData = isDemo ? createDemoResults() : resultsQuery?.data;

  useEffect(() => {
    if (!jobId || isDemo) {
      if (isDemo) setViewerData(createDemoSwingData());
      return;
    }
    getFrames3D(jobId, selectedSwingIndex + 1)
      .then((data) => setViewerData(data))
      .catch(() => setViewerData(null));
  }, [isDemo, jobId, selectedSwingIndex]);

  if (!jobId) return null;

  if (!isReady) {
    return <ProcessingStatus status={statusData} />;
  }

  if (statusData?.status === "failed" || resultsData?.status === "failed") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <p className="text-[var(--color-red)] font-medium">
            {statusData?.error_message || "Analysis failed."}
          </p>
          <Link to="/" className="mt-4 inline-block text-[var(--color-accent)] text-sm hover:underline">
            Try another video
          </Link>
        </Card>
      </div>
    );
  }

  const metrics = resultsData?.metrics;
  if (!metrics) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  const resolvedMetrics = metrics;

  const swingSegments = resolvedMetrics.swing_segments ?? [];
  const hasMultipleSwings = swingSegments.length > 1;
  const selectedSwingNumber = selectedSwingIndex + 1;
  const videoSrc = artifactUrl(jobId, hasMultipleSwings ? `annotated_swing_${selectedSwingNumber}.mp4` : "annotated.mp4");
  const executiveSummary = buildExecutiveSummary(resolvedMetrics, resultsData?.coaching);
  const reliabilityNote = useMemo(() => {
    const unreliable = resolvedMetrics.analysis_quality?.unreliable_metrics ?? {};
    if (!("attack_angle_deg" in unreliable || "head_displacement_total" in unreliable || "x_factor_at_contact" in unreliable)) {
      return null;
    }
    return "Use this view for timing, shape, path, and finish. Exact rotation and bat or ball measurements are estimated or unavailable on this clip.";
  }, [resolvedMetrics.analysis_quality?.unreliable_metrics]);
  const hideHeadCallout = Boolean(resolvedMetrics.analysis_quality?.unreliable_metrics?.head_displacement_total);

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
        <PhaseConfidenceBanner
          isCurrentAnalysis={resultsData?.is_current_analysis}
          analysisVersion={resultsData?.analysis_version}
          measurementReliability={resolvedMetrics.measurement_reliability ?? null}
        />

        <section
          aria-label="Executive summary and annotated video"
          className="overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,rgba(13,18,28,0.98),rgba(22,28,38,0.94))] shadow-[0_24px_80px_rgba(0,0,0,0.28)]"
        >
          <div className="grid gap-0 xl:grid-cols-[minmax(0,1.1fr)_minmax(440px,0.95fr)]">
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

        {viewerData ? (
          <section className="rounded-[28px] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[0_18px_70px_rgba(0,0,0,0.18)]">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-accent)]">Swing read</p>
                <h2 className="mt-1 text-xl font-semibold text-[var(--color-text)]">Interpretive replay</h2>
                <p className="mt-2 text-sm leading-6 text-[var(--color-text-dim)]">
                  This scene follows the body motion and estimated bat path so the swing reads as one continuous move through contact.
                </p>
              </div>
              {reliabilityNote ? (
                <p className="max-w-md rounded-[16px] border border-[var(--color-amber)]/35 bg-[var(--color-amber)]/10 px-3 py-2 text-xs leading-5 text-[var(--color-text-dim)]">
                  {reliabilityNote}
                </p>
              ) : null}
            </div>
            <div className="mt-5">
              <AnimatedSwingReplay
                frames={viewerData.frames}
                currentFrame={Math.min(currentFrame, Math.max(viewerData.total_frames - 1, 0))}
                contactFrame={viewerData.contact_frame}
                reliabilityNote={reliabilityNote ?? undefined}
                hideHeadCallout={hideHeadCallout}
                ball={viewerData.ball}
              />
            </div>
          </section>
        ) : null}

        <SwingTakeaways strengths={executiveSummary.strengths} issues={executiveSummary.issues} />

        <DetailsDiagnostics
          analysis={resultsData?.analysis}
          metrics={resolvedMetrics}
          metricDefinitions={DISPLAY_METRICS}
          currentFrame={currentFrame}
          onFrameSelect={handleFrameSelect}
        />
      </main>
    </div>
  );
}
