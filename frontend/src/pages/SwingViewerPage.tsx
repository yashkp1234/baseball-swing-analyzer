import { useState, useEffect, useRef, useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, RotateCcw } from "lucide-react";
import { getFrames3D, artifactUrl } from "@/lib/api";
import type { Swing3DData } from "@/lib/api";
import { PHASE_COLORS } from "@/lib/metrics";
import { HipShoulderDiagram } from "@/components/HipShoulderDiagram";
import { PhaseEnergyChart } from "@/components/PhaseEnergyChart";
import { WhatIfSimulator } from "@/components/WhatIfSimulator";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import type { SwingMetrics } from "@/lib/api";

const PHASE_HUMAN: Record<string, string> = {
  idle: "Idle", stance: "Stance", load: "Load Up",
  stride: "Stride", swing: "Launch", contact: "Contact",
  follow_through: "Follow Through",
};

const SPEEDS = [0.5, 1, 2, 4];

// ── Loading skeleton ──────────────────────────────────────────────────────────
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

// ── Analysis panel card ───────────────────────────────────────────────────────
function Panel({ title, subtitle, accent, children }: {
  title: string;
  subtitle?: string;
  accent?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="rounded-xl border bg-[var(--color-surface)] p-5 flex flex-col gap-4"
      style={{ borderColor: accent ? `${accent}22` : "var(--color-border)" }}
    >
      <div>
        <h2
          className="text-[10px] uppercase font-semibold"
          style={{
            color: accent ?? "var(--color-text-dim)",
            fontFamily: "Barlow Condensed, sans-serif",
            letterSpacing: "0.14em",
          }}
        >
          {title}
        </h2>
        {subtitle && (
          <p className="text-xs text-[var(--color-text-dim)] mt-1 leading-snug">{subtitle}</p>
        )}
      </div>
      {children}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export function SwingViewerPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [data, setData] = useState<Swing3DData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [videoError, setVideoError] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!jobId) return;
    getFrames3D(jobId).then(setData).catch((e) => setError(e.message));
  }, [jobId]);

  // Sync currentFrame to video playback position
  const handleTimeUpdate = useCallback(() => {
    const vid = videoRef.current;
    if (!vid || !data || !vid.duration) return;
    const pct = vid.currentTime / vid.duration;
    setCurrentFrame(Math.min(
      Math.floor(pct * data.total_frames),
      data.total_frames - 1
    ));
  }, [data]);

  // Apply speed changes to the video element
  useEffect(() => {
    if (videoRef.current) videoRef.current.playbackRate = speed;
  }, [speed]);

  const videoSrc = jobId ? artifactUrl(jobId, "annotated.mp4") : null;
  const phase = data ? (data.phase_labels[currentFrame] ?? "—") : null;

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex flex-col">
      {/* Header */}
      <header className="border-b border-[var(--color-border)] px-6 py-3 flex items-center justify-between shrink-0 bg-[var(--color-surface)]">
        <Link
          to={jobId ? `/results/${jobId}` : "/"}
          className="flex items-center gap-2 text-[var(--color-text-dim)] hover:text-[var(--color-text)] transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span className="text-xs uppercase tracking-wider" style={{ fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}>
            Results
          </span>
        </Link>
        <h1
          className="text-sm font-semibold uppercase tracking-widest"
          style={{ fontFamily: "Barlow Condensed, sans-serif", letterSpacing: "0.15em" }}
        >
          Swing <span style={{ color: "var(--color-accent)" }}>Breakdown</span>
        </h1>
        <div className="w-20" />
      </header>

      {/* Body */}
      {error ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-3">
            <p className="text-xs uppercase tracking-widest text-[var(--color-text-dim)]" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>
              Breakdown data unavailable
            </p>
            <p className="text-xs text-[var(--color-text-dim)]" style={{ fontFamily: "DM Mono, monospace" }}>{error}</p>
            <Link to={jobId ? `/results/${jobId}` : "/"} className="text-xs text-[var(--color-accent)] hover:underline">
              ← Return to results
            </Link>
          </div>
        </div>
      ) : !data ? (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 p-4">
          <Shimmer className="h-full min-h-64" />
          <div className="space-y-4">
            <Shimmer className="h-64" />
            <Shimmer className="h-48" />
            <Shimmer className="h-48" />
          </div>
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-0 overflow-hidden animate-fade-in">

          {/* ── LEFT: Video + controls ──────────────────────────────────── */}
          <div className="flex flex-col border-r border-[var(--color-border)] bg-black">
            {/* Video */}
            <div className="relative flex-1 flex items-center justify-center bg-black min-h-48">
              {videoSrc && !videoError ? (
                <video
                  ref={videoRef}
                  src={videoSrc}
                  className="w-full h-full object-contain"
                  autoPlay
                  loop
                  muted
                  playsInline
                  onTimeUpdate={handleTimeUpdate}
                  onError={() => setVideoError(true)}
                />
              ) : (
                <div className="flex flex-col items-center gap-3 p-8 text-center">
                  <div className="w-12 h-12 rounded-full border border-[var(--color-border)] flex items-center justify-center">
                    <RotateCcw className="h-5 w-5 text-[var(--color-text-dim)]" />
                  </div>
                  <p className="text-xs text-[var(--color-text-dim)]" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>
                    {videoError ? "Annotated video unavailable" : "No video source"}
                  </p>
                  <p className="text-[10px] text-[var(--color-text-dim)] opacity-60">
                    Analysis below is still available
                  </p>
                </div>
              )}

              {/* Phase overlay badge */}
              {phase && (
                <div
                  className="absolute top-3 left-3 px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider"
                  style={{
                    fontFamily: "Barlow Condensed, sans-serif",
                    backgroundColor: `${PHASE_COLORS[phase] ?? "#333"}22`,
                    border: `1px solid ${PHASE_COLORS[phase] ?? "#333"}44`,
                    color: PHASE_COLORS[phase] ?? "var(--color-text-dim)",
                    letterSpacing: "0.12em",
                    backdropFilter: "blur(4px)",
                  }}
                >
                  {PHASE_HUMAN[phase] ?? phase}
                </div>
              )}

              {/* Frame counter */}
              <div
                className="absolute top-3 right-3 px-2 py-1 rounded text-[10px] opacity-70"
                style={{
                  fontFamily: "DM Mono, monospace",
                  backgroundColor: "rgba(0,0,0,0.6)",
                  color: "var(--color-text-dim)",
                }}
              >
                {String(currentFrame + 1).padStart(3, "0")} / {data.total_frames}
              </div>
            </div>

            {/* Video controls */}
            <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)] p-4 space-y-3 shrink-0">
              {/* Phase color strip */}
              <div className="flex h-1 rounded-full overflow-hidden">
                {data.phase_labels.map((p, i) => (
                  <div
                    key={i}
                    style={{
                      backgroundColor: PHASE_COLORS[p] ?? "#333",
                      width: `${100 / data.total_frames}%`,
                      opacity: i === currentFrame ? 1 : 0.5,
                    }}
                  />
                ))}
              </div>

              <div className="flex items-center justify-between gap-4">
                {/* Auto-loop indicator */}
                <div className="flex items-center gap-1.5">
                  <RotateCcw className="h-3 w-3 text-[var(--color-accent)]" />
                  <span
                    className="text-[10px] uppercase tracking-wider text-[var(--color-text-dim)]"
                    style={{ fontFamily: "Barlow Condensed, sans-serif", letterSpacing: "0.1em" }}
                  >
                    Looping
                  </span>
                </div>

                {/* FPS */}
                <span
                  className="text-[10px] text-[var(--color-text-dim)]"
                  style={{ fontFamily: "DM Mono, monospace" }}
                >
                  {data.fps.toFixed(0)} FPS
                </span>

                {/* Speed buttons */}
                <div className="flex gap-1">
                  {SPEEDS.map((s) => (
                    <button
                      key={s}
                      onClick={() => setSpeed(s)}
                      className="px-2 py-0.5 rounded text-[10px] transition-colors"
                      style={{
                        fontFamily: "DM Mono, monospace",
                        backgroundColor: speed === s ? "var(--color-accent)" : "var(--color-surface-2)",
                        color: speed === s ? "var(--color-bg)" : "var(--color-text-dim)",
                        fontWeight: speed === s ? 700 : 400,
                      }}
                    >
                      {s}×
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* ── RIGHT: Analysis panels ──────────────────────────────────── */}
          <div className="overflow-y-auto p-4 space-y-4">
            <ErrorBoundary>
              <Panel
                title="Hip vs Shoulder Rotation"
                subtitle="Top-down view — hips and shoulders through the swing"
                accent="#4A90D9"
              >
                <HipShoulderDiagram
                  frames={data.frames}
                  currentFrame={currentFrame}
                  contactFrame={data.contact_frame}
                />
              </Panel>
            </ErrorBoundary>

            <ErrorBoundary>
              <Panel
                title="Power Through Your Swing"
                subtitle="Where bat speed built up — and where it leaked"
                accent="#00FF87"
              >
                <PhaseEnergyChart
                  frames={data.frames}
                  phaseLabels={data.phase_labels}
                  energyLossEvents={data.energy_loss_events}
                />
              </Panel>
            </ErrorBoundary>

            <ErrorBoundary>
              <Panel
                title="What If You Fixed This?"
                subtitle="See how improving these mechanics changes your score"
                accent="#FFD700"
              >
                <WhatIfSimulator metrics={data.metrics as unknown as SwingMetrics} />
              </Panel>
            </ErrorBoundary>
          </div>
        </div>
      )}
    </div>
  );
}
