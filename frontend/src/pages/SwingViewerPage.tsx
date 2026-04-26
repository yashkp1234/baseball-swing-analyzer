import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Pause, Play, RotateCcw } from "lucide-react";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { FixTogglePanel } from "@/components/FixTogglePanel";
import { PhaseTimeline } from "@/components/PhaseTimeline";
import { SwingSkeletonViewer } from "@/components/SwingSkeletonViewer";
import { getFrames3D, projectSwing } from "@/lib/api";
import type { ProjectionResponse, Swing3DData } from "@/lib/api";
import { PHASE_COLORS, PHASE_LABELS } from "@/lib/metrics";

const SPEEDS = [0.5, 1, 2];
const DEFAULT_FIX = {
  id: "lower_half_timing",
  label: "Fix lower-half timing",
  coach_text: "Keep the stride controlled so the front side braces before the swing turns.",
};

function Shimmer({ className = "" }: { className?: string }) {
  return (
    <div
      className={`rounded-lg ${className}`}
      style={{
        background: "linear-gradient(90deg, var(--color-surface-2) 0%, var(--color-surface) 50%, var(--color-surface-2) 100%)",
        backgroundSize: "200% 100%",
        animation: "shimmer 1.5s infinite",
      }}
    />
  );
}

export function SwingViewerPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [searchParams] = useSearchParams();
  const [baseData, setBaseData] = useState<Swing3DData | null>(null);
  const [activeData, setActiveData] = useState<Swing3DData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [playing, setPlaying] = useState(true);
  const [viewerError, setViewerError] = useState<string | null>(null);
  const [resetCameraToken, setResetCameraToken] = useState(0);
  const [baselineProjection, setBaselineProjection] = useState<ProjectionResponse["baseline"] | null>(null);
  const [projection, setProjection] = useState<ProjectionResponse["projection"] | null>(null);
  const [fix, setFix] = useState<ProjectionResponse["fix"] | null>(DEFAULT_FIX);
  const [fixEnabled, setFixEnabled] = useState(false);
  const [projectionPending, setProjectionPending] = useState(false);
  const [projectionError, setProjectionError] = useState<string | null>(null);
  const latestProjectionRequest = useRef(0);
  const selectedSwing = useMemo(() => {
    const rawValue = searchParams.get("swing");
    if (!rawValue) return undefined;
    const parsed = Number.parseInt(rawValue, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
  }, [searchParams]);

  useEffect(() => {
    if (!jobId) return;
    getFrames3D(jobId, selectedSwing)
      .then((frames) => {
        setBaseData(frames);
        setActiveData(frames);
      })
      .catch((requestError: Error) => setError(requestError.message));
  }, [jobId, selectedSwing]);

  useEffect(() => {
    if (!jobId || !baseData) return;
    const requestId = ++latestProjectionRequest.current;
    setProjectionPending(true);
    projectSwing(jobId, {}, selectedSwing)
      .then((result) => {
        if (requestId !== latestProjectionRequest.current) return;
        setBaselineProjection(result.baseline);
        setProjection(null);
        setFix(result.fix ?? DEFAULT_FIX);
        setProjectionError(null);
      })
      .catch((requestError: Error) => {
        if (requestId !== latestProjectionRequest.current) return;
        setProjectionError(requestError.message);
      })
      .finally(() => {
        if (requestId === latestProjectionRequest.current) setProjectionPending(false);
      });
  }, [baseData, jobId, selectedSwing]);

  useEffect(() => {
    const totalFrames = activeData?.total_frames ?? 0;
    if (!playing || totalFrames <= 1 || !activeData) return;
    const intervalMs = Math.max(20, 1000 / (activeData.fps * speed));
    const timer = window.setInterval(() => {
      setCurrentFrame((frame) => (frame + 1) % totalFrames);
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [activeData, playing, speed]);

  useEffect(() => {
    if (!activeData) return;
    setCurrentFrame((frame) => Math.min(frame, Math.max(activeData.total_frames - 1, 0)));
  }, [activeData]);

  const handleFixToggle = useCallback(async (enabled: boolean) => {
    if (!jobId || !baseData) return;
    setFixEnabled(enabled);
    setPlaying(true);

    if (!enabled) {
      latestProjectionRequest.current += 1;
      setProjection(null);
      setProjectionError(null);
      setActiveData(baseData);
      return;
    }

    const requestId = ++latestProjectionRequest.current;
    setProjectionPending(true);
    setProjectionError(null);
    try {
      const result = await projectSwing(jobId, { fix_id: "lower_half_timing" }, selectedSwing);
      if (requestId !== latestProjectionRequest.current) return;
      setBaselineProjection(result.baseline);
      setProjection(result.projection);
      setFix(result.fix ?? DEFAULT_FIX);
      setActiveData(result.viewer);
    } catch (requestError) {
      if (requestId !== latestProjectionRequest.current) return;
      setProjectionError(requestError instanceof Error ? requestError.message : "Projection failed");
      setFixEnabled(false);
      setActiveData(baseData);
    } finally {
      if (requestId === latestProjectionRequest.current) setProjectionPending(false);
      }
  }, [baseData, jobId, selectedSwing]);

  const displayedData = activeData ?? baseData;
  const activePhase = displayedData ? displayedData.phase_labels[currentFrame] ?? "idle" : "idle";
  const activePhaseLabel = PHASE_LABELS[activePhase] ?? activePhase.replaceAll("_", " ");
  const projectedViewActive = fixEnabled && Boolean(projection);

  const phaseStrip = useMemo(() => {
    if (!displayedData) return null;
    return displayedData.phase_labels.map((phase, index) => (
      <div
        key={`${phase}-${index}`}
        style={{
          backgroundColor: PHASE_COLORS[phase] ?? "#333",
          width: `${100 / displayedData.total_frames}%`,
          opacity: index === currentFrame ? 1 : 0.42,
        }}
      />
    ));
  }, [currentFrame, displayedData]);

  if (error) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)]">
        <div className="flex h-full min-h-screen items-center justify-center">
          <div className="space-y-3 text-center">
            <p className="text-xs uppercase tracking-widest text-[var(--color-text-dim)]">
              Breakdown data unavailable
            </p>
            <p className="text-xs text-[var(--color-text-dim)]">{error}</p>
            <Link to={jobId ? `/results/${jobId}` : "/"} className="text-xs text-[var(--color-accent)] hover:underline">
              Return to results
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!displayedData) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)] p-4">
        <div className="grid min-h-[calc(100vh-2rem)] grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Shimmer className="min-h-96" />
          <div className="space-y-4">
            <Shimmer className="h-48" />
            <Shimmer className="h-64" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen overflow-hidden bg-[var(--color-bg)]">
      <header className="flex h-14 items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6">
        <Link to={jobId ? `/results/${jobId}` : "/"} className="flex items-center gap-2 text-[var(--color-text-dim)] transition-colors hover:text-[var(--color-text)]">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span className="text-xs font-semibold uppercase tracking-wider">Results</span>
        </Link>
        <h1 className="text-sm font-semibold uppercase tracking-widest">
          Swing <span className="text-[var(--color-accent)]">Breakdown</span>
        </h1>
        <div className="w-20" />
      </header>

      <main className="grid h-[calc(100vh-56px)] grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_380px]">
        <section className="flex min-h-0 flex-col border-r border-[var(--color-border)] bg-black">
          <div className="relative min-h-0 flex-1">
            {viewerError ? (
              <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
                <p className="text-xs uppercase tracking-widest text-[var(--color-text-dim)]">
                  Interactive view unavailable
                </p>
                <p className="text-xs text-[var(--color-text-dim)]">{viewerError}</p>
              </div>
            ) : (
              <SwingSkeletonViewer
                data={displayedData}
                currentFrame={currentFrame}
                projected={projectedViewActive}
                resetToken={resetCameraToken}
                onError={setViewerError}
              />
            )}

            <div
              className="absolute left-3 top-3 rounded-md border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider"
              style={{
                backgroundColor: `${PHASE_COLORS[activePhase] ?? "#333"}22`,
                borderColor: `${PHASE_COLORS[activePhase] ?? "#333"}44`,
                color: PHASE_COLORS[activePhase] ?? "var(--color-text-dim)",
                backdropFilter: "blur(4px)",
              }}
            >
              {activePhaseLabel}
            </div>

            <div className="absolute right-3 top-3 rounded bg-black/60 px-2 py-1 text-[10px] text-[var(--color-text-dim)]">
              {String(currentFrame + 1).padStart(3, "0")} / {displayedData.total_frames}
            </div>

            {projectedViewActive ? (
              <div className="absolute bottom-3 left-3 rounded-md border border-[#ffd54a55] bg-[#ffd54a22] px-2.5 py-1 text-[10px] uppercase tracking-wider text-[#ffd54a]">
                Fix Preview
              </div>
            ) : null}
          </div>

          <div className="space-y-3 border-t border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <div className="flex h-1 overflow-hidden rounded-full">{phaseStrip}</div>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPlaying((value) => !value)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-text)] hover:border-[var(--color-accent)]"
                  aria-label={playing ? "Pause playback" : "Play playback"}
                >
                  {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </button>
                <button
                  type="button"
                  onClick={() => setResetCameraToken((token) => token + 1)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-text)] hover:border-[var(--color-accent)]"
                  aria-label="Reset camera"
                >
                  <RotateCcw className="h-4 w-4" />
                </button>
              </div>

              <div className="flex items-center gap-1">
                {SPEEDS.map((value) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setSpeed(value)}
                    className="rounded px-2 py-0.5 text-[10px] transition-colors"
                    style={{
                      backgroundColor: speed === value ? "var(--color-accent)" : "var(--color-surface-2)",
                      color: speed === value ? "var(--color-bg)" : "var(--color-text-dim)",
                      fontWeight: speed === value ? 700 : 400,
                    }}
                  >
                    {value}x
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        <aside className="flex min-h-0 flex-col gap-4 overflow-auto bg-[var(--color-bg)] p-4">
          <ErrorBoundary>
            <FixTogglePanel
              enabled={fixEnabled}
              pending={projectionPending}
              baseline={baselineProjection}
              projection={projection}
              fix={fix}
              error={projectionError}
              onToggle={handleFixToggle}
            />
          </ErrorBoundary>

          <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <h2 className="text-sm font-semibold text-[var(--color-text)]">Swing Loop</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">
              Watch how the move changes when the fix is on. The bat and ball are estimated from the pose.
            </p>
            <div className="mt-4">
              <PhaseTimeline
                phaseLabels={displayedData.phase_labels}
                totalFrames={displayedData.total_frames}
                contactFrame={displayedData.contact_frame}
                stridePlantFrame={displayedData.stride_plant_frame}
                currentFrame={currentFrame}
                onFrameSelect={(frame) => {
                  setPlaying(false);
                  setCurrentFrame(frame);
                }}
              />
            </div>
          </section>

          <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <h2 className="text-sm font-semibold text-[var(--color-text)]">What Changed</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--color-text-dim)]">
              The fix preview adds a cleaner lower-half sequence: more separation into contact and less upper-body drift. That changes the estimated score and batted-ball range without claiming measured ball flight.
            </p>
          </section>
        </aside>
      </main>
    </div>
  );
}
