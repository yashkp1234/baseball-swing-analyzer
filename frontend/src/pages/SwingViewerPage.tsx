import { useState, useEffect, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Play, Pause } from "lucide-react";
import { getFrames3D } from "@/lib/api";
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

const SPEEDS = [0.25, 0.5, 1, 2];

// ── Loading skeleton ─────────────────────────────────────────────────────────
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

function LoadingSkeleton() {
  return (
    <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 p-4">
      <Shimmer className="h-64" />
      <Shimmer className="h-64" />
      <Shimmer className="h-48 lg:col-span-2" />
    </div>
  );
}

// ── Section panel ────────────────────────────────────────────────────────────
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
          className="text-xs uppercase tracking-widest font-semibold"
          style={{
            color: accent ?? "var(--color-text-dim)",
            fontFamily: "Barlow Condensed, sans-serif",
            letterSpacing: "0.12em",
          }}
        >
          {title}
        </h2>
        {subtitle && (
          <p className="text-sm text-[var(--color-text-dim)] mt-1 leading-snug">{subtitle}</p>
        )}
      </div>
      {children}
    </div>
  );
}

// ── Frame scrubber ───────────────────────────────────────────────────────────
function FrameScrubber({
  data, currentFrame, onChange,
}: { data: Swing3DData; currentFrame: number; onChange: (f: number) => void }) {
  const total = data.total_frames;
  const phase = data.phase_labels[currentFrame] ?? "—";
  const contactPct = total > 1 ? (data.contact_frame / (total - 1)) * 100 : 50;
  const stridePct =
    data.stride_plant_frame != null && total > 1
      ? (data.stride_plant_frame / (total - 1)) * 100
      : null;

  return (
    <div className="relative w-full">
      {/* Phase color band */}
      <div className="flex h-1.5 rounded-full overflow-hidden mb-2.5">
        {data.phase_labels.map((p, i) => (
          <div
            key={i}
            style={{ backgroundColor: PHASE_COLORS[p] ?? "#333", width: `${100 / total}%`, opacity: 0.8 }}
          />
        ))}
      </div>

      {/* Markers */}
      <div className="relative h-0">
        {stridePct != null && (
          <div
            className="absolute w-1.5 h-1.5 rounded-full bg-white/60 -top-3 -translate-x-1/2"
            style={{ left: `${stridePct}%` }}
            title="Stride plant"
          />
        )}
        <div
          className="absolute w-2.5 h-2.5 rounded-full -top-3.5 -translate-x-1/2"
          style={{
            left: `${contactPct}%`,
            backgroundColor: "#FFD700",
            boxShadow: "0 0 6px rgba(255,215,0,0.6)",
          }}
          title="Contact"
        />
      </div>

      <input
        type="range"
        min={0}
        max={total - 1}
        value={currentFrame}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label="Frame scrubber"
        className="w-full h-1.5 appearance-none bg-[var(--color-surface-2)] rounded-full cursor-pointer"
      />

      <div className="flex justify-between text-[11px] text-[var(--color-text-dim)] mt-2" style={{ fontFamily: "DM Mono, monospace" }}>
        <span>{String(currentFrame + 1).padStart(3, "0")} / {total}</span>
        <span style={{ color: PHASE_COLORS[phase] ?? "inherit", fontFamily: "Barlow Condensed, sans-serif", letterSpacing: "0.08em", fontWeight: 600, fontSize: "0.7rem" }}>
          {(PHASE_HUMAN[phase] ?? phase).toUpperCase()}
        </span>
        <span>{data.fps.toFixed(0)} FPS</span>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export function SwingViewerPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [data, setData] = useState<Swing3DData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) return;
    getFrames3D(jobId)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [jobId]);

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (!isPlaying || !data) return;
    const ms = 1000 / (data.fps * speed);
    intervalRef.current = setInterval(() => {
      setCurrentFrame((f) => {
        if (f >= data.total_frames - 1) { setIsPlaying(false); return f; }
        return f + 1;
      });
    }, ms);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [isPlaying, speed, data]);

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex flex-col">
      {/* Header */}
      <header className="border-b border-[var(--color-border)] px-6 py-3 flex items-center justify-between shrink-0 bg-[var(--color-surface)]">
        <Link
          to={jobId ? `/results/${jobId}` : "/"}
          className="flex items-center gap-2 text-[var(--color-text-dim)] hover:text-[var(--color-text)] transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span className="text-xs uppercase tracking-wider" style={{ fontFamily: "Barlow Condensed, sans-serif", fontWeight: 600 }}>Results</span>
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
        <LoadingSkeleton />
      ) : (
        <>
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 p-4 animate-fade-in">
            <ErrorBoundary>
              <Panel
                title="Hip vs Shoulder Rotation"
                subtitle="Top-down view — how your hips and shoulders moved through the swing"
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

            <div className="lg:col-span-2">
              <ErrorBoundary>
                <Panel
                  title="What If You Fixed This?"
                  subtitle="Drag the sliders to see how improving these two mechanics would change your score"
                  accent="#FFD700"
                >
                  <WhatIfSimulator metrics={data.metrics as unknown as SwingMetrics} />
                </Panel>
              </ErrorBoundary>
            </div>
          </div>

          {/* Scrubber bar */}
          <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-4 shrink-0">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsPlaying((p) => !p)}
                aria-label={isPlaying ? "Pause" : "Play"}
                className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all hover:brightness-110"
                style={{
                  backgroundColor: "var(--color-accent)",
                  boxShadow: isPlaying ? "0 0 12px rgba(0,255,135,0.4)" : undefined,
                }}
              >
                {isPlaying
                  ? <Pause className="h-3.5 w-3.5 text-black" />
                  : <Play className="h-3.5 w-3.5 text-black" />}
              </button>

              <div className="flex-1">
                <FrameScrubber data={data} currentFrame={currentFrame} onChange={setCurrentFrame} />
              </div>

              <div className="flex gap-1 shrink-0">
                {SPEEDS.map((s) => (
                  <button
                    key={s}
                    onClick={() => setSpeed(s)}
                    className="px-2 py-1 rounded text-[10px] transition-colors"
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
        </>
      )}
    </div>
  );
}
