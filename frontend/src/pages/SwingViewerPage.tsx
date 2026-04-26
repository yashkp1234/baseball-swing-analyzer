import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Pause, Play, RotateCcw } from "lucide-react";
import { getFrames3D, getJobResults, projectSwing } from "@/lib/api";
import type { AnalysisSummary as AnalysisSummaryData, ProjectionResponse, SportProfile, Swing3DData } from "@/lib/api";
import { PHASE_COLORS } from "@/lib/metrics";
import { HipShoulderDiagram } from "@/components/HipShoulderDiagram";
import { PhaseEnergyChart } from "@/components/PhaseEnergyChart";
import { WhatIfSimulator, type ProjectionInput } from "@/components/WhatIfSimulator";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AnalysisSummary } from "@/components/AnalysisSummary";
import { SwingSkeletonViewer } from "@/components/SwingSkeletonViewer";

const PHASE_HUMAN: Record<string, string> = {
  idle: "Idle",
  stance: "Stance",
  load: "Load Up",
  stride: "Stride",
  swing: "Launch",
  contact: "Contact",
  follow_through: "Follow Through",
};

const SPEEDS = [0.5, 1, 2, 4];
const TABS = [
  { id: "overview", label: "Overview" },
  { id: "kinematics", label: "Kinematics" },
  { id: "whatif", label: "What If" },
] as const;

type ViewerTab = (typeof TABS)[number]["id"];

function sportLabel(profile: SportProfile | null | undefined): string {
  if (!profile || profile.label === "unknown") return "Not confidently detected";
  return profile.label === "baseball" ? "Baseball" : "Softball";
}

function sportNote(profile: SportProfile | null | undefined): string {
  if (!profile || profile.label === "unknown") {
    return "Using shared hitting guidance because sport was not confidently detected.";
  }
  return `Using ${profile.label}-aware wording where coaching and estimate framing differ.`;
}

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

function Panel({ title, subtitle, accent, children }: {
  title: string;
  subtitle?: string;
  accent?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-full flex-col gap-4 rounded-xl border bg-[var(--color-surface)] p-5" style={{ borderColor: accent ? `${accent}22` : "var(--color-border)" }}>
      <div>
        <h2
          className="text-[10px] uppercase font-semibold"
          style={{ color: accent ?? "var(--color-text-dim)", fontFamily: "Barlow Condensed, sans-serif", letterSpacing: "0.14em" }}
        >
          {title}
        </h2>
        {subtitle ? <p className="mt-1 text-xs leading-snug text-[var(--color-text-dim)]">{subtitle}</p> : null}
      </div>
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  );
}

export function SwingViewerPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [baseData, setBaseData] = useState<Swing3DData | null>(null);
  const [activeData, setActiveData] = useState<Swing3DData | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisSummaryData | null>(null);
  const [sportProfile, setSportProfile] = useState<SportProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [playing, setPlaying] = useState(true);
  const [viewerError, setViewerError] = useState<string | null>(null);
  const [resetCameraToken, setResetCameraToken] = useState(0);
  const [activeTab, setActiveTab] = useState<ViewerTab>("overview");
  const [baselineProjection, setBaselineProjection] = useState<ProjectionResponse["baseline"] | null>(null);
  const [projection, setProjection] = useState<ProjectionResponse["projection"] | null>(null);
  const [projectionPending, setProjectionPending] = useState(false);
  const [projectionError, setProjectionError] = useState<string | null>(null);
  const [whatIfResetToken, setWhatIfResetToken] = useState(0);
  const latestProjectionRequest = useRef(0);

  useEffect(() => {
    if (!jobId) return;
    Promise.all([getFrames3D(jobId), getJobResults(jobId)])
      .then(([frames, results]) => {
        setBaseData(frames);
        setActiveData(frames);
        setAnalysis(results.analysis);
        setSportProfile(results.sport_profile);
      })
      .catch((requestError: Error) => setError(requestError.message));
  }, [jobId]);

  useEffect(() => {
    if (!jobId || !baseData) return;
    const requestId = ++latestProjectionRequest.current;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setProjectionPending(true);
    projectSwing(jobId, { x_factor_delta_deg: 0, head_stability_delta_norm: 0 })
      .then((result) => {
        if (requestId !== latestProjectionRequest.current) return;
        setBaselineProjection(result.baseline);
        setProjection(null);
        if (result.sport_profile) {
          setSportProfile(result.sport_profile);
        }
        setProjectionError(null);
      })
      .catch((requestError: Error) => {
        if (requestId !== latestProjectionRequest.current) return;
        setProjectionError(requestError.message);
      })
      .finally(() => {
        if (requestId === latestProjectionRequest.current) {
          setProjectionPending(false);
        }
      });
  }, [baseData, jobId]);

  useEffect(() => {
    const totalFrames = activeData?.total_frames ?? 0;
    if (!playing || totalFrames <= 1 || !activeData) return;
    const intervalMs = Math.max(16, 1000 / (activeData.fps * speed));
    const timer = window.setInterval(() => {
      setCurrentFrame((frame) => (frame + 1) % totalFrames);
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [activeData, playing, speed]);

  useEffect(() => {
    if (!activeData) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCurrentFrame((frame) => Math.min(frame, Math.max(activeData.total_frames - 1, 0)));
  }, [activeData]);

  const handleProjection = useCallback(async (input: ProjectionInput) => {
    if (!jobId || !baseData) return;
    const requestId = ++latestProjectionRequest.current;
    setProjectionPending(true);
    setProjectionError(null);

    try {
      const result = await projectSwing(jobId, input);
      if (requestId !== latestProjectionRequest.current) return;
      setBaselineProjection(result.baseline);
      const isBaseline = input.x_factor_delta_deg === 0 && input.head_stability_delta_norm === 0;
      setProjection(isBaseline ? null : result.projection);
      if (result.sport_profile) {
        setSportProfile(result.sport_profile);
      }
      setActiveData(isBaseline ? baseData : result.viewer);
    } catch (requestError) {
      if (requestId !== latestProjectionRequest.current) return;
      setProjectionError(requestError instanceof Error ? requestError.message : "Projection failed");
    } finally {
      if (requestId === latestProjectionRequest.current) {
        setProjectionPending(false);
      }
    }
  }, [baseData, jobId]);

  const handleResetProjection = useCallback(() => {
    if (!baseData) return;
    latestProjectionRequest.current += 1;
    setProjection(null);
    setProjectionError(null);
    setActiveData(baseData);
    setWhatIfResetToken((token) => token + 1);
    void handleProjection({ x_factor_delta_deg: 0, head_stability_delta_norm: 0 });
  }, [baseData, handleProjection]);

  const activePhase = activeData ? activeData.phase_labels[currentFrame] ?? "idle" : "idle";
  const displayedData = activeData ?? baseData;
  const projectedViewActive = Boolean(projection);

  const phaseStrip = useMemo(() => {
    if (!displayedData) return null;
    return displayedData.phase_labels.map((phase, index) => (
      <div
        key={`${phase}-${index}`}
        style={{
          backgroundColor: PHASE_COLORS[phase] ?? "#333",
          width: `${100 / displayedData.total_frames}%`,
          opacity: index === currentFrame ? 1 : 0.45,
        }}
      />
    ));
  }, [currentFrame, displayedData]);

  if (error) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)]">
        <div className="flex h-full min-h-screen items-center justify-center">
          <div className="space-y-3 text-center">
            <p className="text-xs uppercase tracking-widest text-[var(--color-text-dim)]" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>
              Breakdown data unavailable
            </p>
            <p className="text-xs text-[var(--color-text-dim)]" style={{ fontFamily: "DM Mono, monospace" }}>{error}</p>
            <Link to={jobId ? `/results/${jobId}` : "/"} className="text-xs text-[var(--color-accent)] hover:underline">
              ← Return to results
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!displayedData) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)]">
        <div className="grid min-h-screen grid-cols-1 gap-4 p-4 lg:grid-cols-2">
          <Shimmer className="h-full min-h-64" />
          <div className="space-y-4">
            <Shimmer className="h-64" />
            <Shimmer className="h-48" />
            <Shimmer className="h-48" />
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
          <span className="text-xs uppercase tracking-wider" style={{ fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}>
            Results
          </span>
        </Link>
        <h1 className="text-sm font-semibold uppercase tracking-widest" style={{ fontFamily: "Barlow Condensed, sans-serif", letterSpacing: "0.15em" }}>
          Swing <span style={{ color: "var(--color-accent)" }}>Breakdown</span>
        </h1>
        <div className="w-20" />
      </header>

      <main className="grid h-[calc(100vh-56px)] grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,1.45fr)_420px]">
        <section className="flex min-h-0 flex-col border-r border-[var(--color-border)] bg-black">
          <div className="relative min-h-0 flex-1">
            {viewerError ? (
              <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
                <p className="text-xs uppercase tracking-widest text-[var(--color-text-dim)]" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>
                  Interactive 3D view unavailable
                </p>
                <p className="text-xs text-[var(--color-text-dim)]" style={{ fontFamily: "DM Mono, monospace" }}>{viewerError}</p>
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
                fontFamily: "Barlow Condensed, sans-serif",
                backgroundColor: `${PHASE_COLORS[activePhase] ?? "#333"}22`,
                borderColor: `${PHASE_COLORS[activePhase] ?? "#333"}44`,
                color: PHASE_COLORS[activePhase] ?? "var(--color-text-dim)",
                backdropFilter: "blur(4px)",
              }}
            >
              {PHASE_HUMAN[activePhase] ?? activePhase}
            </div>

            <div className="absolute right-3 top-3 rounded bg-black/60 px-2 py-1 text-[10px] text-[var(--color-text-dim)]" style={{ fontFamily: "DM Mono, monospace" }}>
              {String(currentFrame + 1).padStart(3, "0")} / {displayedData.total_frames}
            </div>

            {projectedViewActive ? (
              <div className="absolute bottom-3 left-3 rounded-md border border-[#ffd54a55] bg-[#ffd54a22] px-2.5 py-1 text-[10px] uppercase tracking-wider text-[#ffd54a]" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>
                Projected View
              </div>
            ) : null}
          </div>

          <div className="space-y-3 border-t border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <div className="flex h-1 overflow-hidden rounded-full">{phaseStrip}</div>
            <input
              type="range"
              min={0}
              max={Math.max(displayedData.total_frames - 1, 0)}
              value={currentFrame}
              onChange={(event) => {
                setPlaying(false);
                setCurrentFrame(Number(event.target.value));
              }}
              className="w-full accent-[var(--color-accent)]"
            />
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
                      fontFamily: "DM Mono, monospace",
                      backgroundColor: speed === value ? "var(--color-accent)" : "var(--color-surface-2)",
                      color: speed === value ? "var(--color-bg)" : "var(--color-text-dim)",
                      fontWeight: speed === value ? 700 : 400,
                    }}
                  >
                    {value}×
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        <aside className="flex min-h-0 flex-col overflow-hidden bg-[var(--color-bg)]">
          <div className="flex items-center gap-2 border-b border-[var(--color-border)] px-4 py-3">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className="rounded-md px-3 py-1.5 text-[11px] uppercase tracking-widest transition-colors"
                style={{
                  fontFamily: "Barlow Condensed, sans-serif",
                  backgroundColor: activeTab === tab.id ? "var(--color-accent)" : "var(--color-surface-2)",
                  color: activeTab === tab.id ? "var(--color-bg)" : "var(--color-text-dim)",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="min-h-0 flex-1 overflow-hidden p-4">
            {activeTab === "overview" ? (
              <div className="flex h-full flex-col gap-4">
                <AnalysisSummary analysis={analysis} />
                <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-sm font-semibold">Detected Sport</h3>
                    <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-dim)]">
                      {sportLabel(sportProfile)}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--color-text-dim)]">{sportNote(sportProfile)}</p>
                </div>
                <ErrorBoundary>
                  <Panel title="Power Through Your Swing" subtitle="Where energy built up — and where it leaked" accent="#00FF87">
                    <PhaseEnergyChart
                      frames={displayedData.frames}
                      phaseLabels={displayedData.phase_labels}
                      energyLossEvents={displayedData.energy_loss_events}
                    />
                  </Panel>
                </ErrorBoundary>
              </div>
            ) : null}

            {activeTab === "kinematics" ? (
              <ErrorBoundary>
                <Panel title="Hip vs Shoulder Rotation" subtitle="Top-down yaw — hips and shoulders through the swing" accent="#4A90D9">
                  <HipShoulderDiagram
                    frames={displayedData.frames}
                    currentFrame={currentFrame}
                    contactFrame={displayedData.contact_frame}
                  />
                </Panel>
              </ErrorBoundary>
            ) : null}

            {activeTab === "whatif" ? (
      <ErrorBoundary>
        <Panel title="What If You Fixed This?" subtitle="Release a slider to project a new swing path and outcome" accent="#FFD700">
          <WhatIfSimulator
            key={whatIfResetToken}
            baselineXFactor={Number(displayedData.metrics.x_factor_at_contact ?? 0)}
            baselineHeadDisplacementPx={Number(displayedData.metrics.head_displacement_total ?? 0)}
            sportProfile={sportProfile}
            baseline={baselineProjection}
            projection={projection}
            pending={projectionPending}
            error={projectionError}
            onApply={handleProjection}
            onReset={handleResetProjection}
          />
        </Panel>
              </ErrorBoundary>
            ) : null}
          </div>
        </aside>
      </main>
    </div>
  );
}
