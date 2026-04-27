import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Pause, Play } from "lucide-react";
import { AnimatedSwingReplay } from "@/components/AnimatedSwingReplay";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PhaseEnergyChart } from "@/components/PhaseEnergyChart";
import { PhaseTimeline } from "@/components/PhaseTimeline";
import { WhatIfSimulator } from "@/components/WhatIfSimulator";
import { getFrames3D } from "@/lib/api";
import type { SwingMetrics, Swing3DData } from "@/lib/api";
import { PHASE_LABELS } from "@/lib/metrics";

export const PLAYBACK_SPEEDS = [0.25, 0.5, 1] as const;
export const DEFAULT_PLAYBACK_SPEED = PLAYBACK_SPEEDS[0];

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

function metricsFromViewer(data: Swing3DData | null): Partial<SwingMetrics> {
  if (!data) return {};
  return {
    phase_labels: data.phase_labels,
    contact_frame: data.contact_frame,
    stride_plant_frame: data.stride_plant_frame,
    fps: data.fps,
    frames: data.total_frames,
    ...(data.metrics as Partial<SwingMetrics>),
  };
}

export function SwingViewerPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [searchParams] = useSearchParams();
  const [data, setData] = useState<Swing3DData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [speed, setSpeed] = useState<number>(DEFAULT_PLAYBACK_SPEED);
  const [playing, setPlaying] = useState(true);

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
        setData(frames);
        setError(null);
      })
      .catch((requestError: Error) => setError(requestError.message));
  }, [jobId, selectedSwing]);

  useEffect(() => {
    const totalFrames = data?.total_frames ?? 0;
    if (!playing || totalFrames <= 1 || !data) return;
    const intervalMs = Math.max(24, 1000 / (data.fps * speed));
    const timer = window.setInterval(() => {
      setCurrentFrame((frame) => (frame + 1) % totalFrames);
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [data, playing, speed]);

  useEffect(() => {
    if (!data) return;
    setCurrentFrame((frame) => Math.min(frame, Math.max(data.total_frames - 1, 0)));
  }, [data]);

  const metrics = useMemo(() => metricsFromViewer(data), [data]);
  const currentPhase = data ? data.phase_labels[currentFrame] ?? "idle" : "idle";
  const currentPhaseLabel = PHASE_LABELS[currentPhase] ?? currentPhase.replaceAll("_", " ");

  if (error) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)]">
        <div className="flex h-full min-h-screen items-center justify-center">
          <div className="space-y-3 text-center">
            <p className="text-xs uppercase tracking-widest text-[var(--color-text-dim)]">Breakdown data unavailable</p>
            <p className="text-xs text-[var(--color-text-dim)]">{error}</p>
            <Link to={jobId ? `/results/${jobId}` : "/"} className="text-xs text-[var(--color-accent)] hover:underline">
              Return to results
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)] p-4 lg:p-6">
        <div className="grid min-h-[calc(100vh-2rem)] grid-cols-1 gap-4 lg:grid-cols-2">
          <Shimmer className="min-h-72" />
          <Shimmer className="min-h-72" />
          <Shimmer className="min-h-64 lg:col-span-2" />
          <Shimmer className="h-24 lg:col-span-2" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <header className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-4">
        <Link
          to={jobId ? `/results/${jobId}` : "/"}
          className="flex items-center gap-2 text-[var(--color-text-dim)] transition-colors hover:text-[var(--color-text)]"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm font-medium">Back to Results</span>
        </Link>
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Swing Breakdown</h1>
        <div className="w-24" />
      </header>

      <main className="mx-auto flex min-h-[calc(100vh-73px)] max-w-[1680px] flex-col px-5 py-6 lg:px-8">
        <div className="grid flex-1 gap-6 lg:grid-cols-2">
          <section className="rounded-[24px] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold text-[var(--color-text)]">What did your body do?</h2>
                <p className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">
                  Start with the actual body replay. It shows the move frame by frame, with the recent path left behind so you can read how the swing really traveled.
                </p>
              </div>
              <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1.5 text-xs font-semibold text-[var(--color-text-dim)]">
                {currentPhaseLabel}
              </div>
            </div>
            <div className="mt-5 flex items-center justify-center">
              <AnimatedSwingReplay frames={data.frames} currentFrame={currentFrame} contactFrame={data.contact_frame} />
            </div>
          </section>

          <section className="rounded-[24px] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <div>
              <h2 className="text-base font-semibold text-[var(--color-text)]">Where did power build and leak?</h2>
              <p className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">
                Each phase shows the average hand speed in that part of the swing. Large drops are flagged so you can see where momentum backed up.
              </p>
            </div>
            <div className="mt-5">
              <PhaseEnergyChart frames={data.frames} phaseLabels={data.phase_labels} energyLossEvents={data.energy_loss_events} />
            </div>
          </section>

          <div className="lg:col-span-2">
            <ErrorBoundary>
              <WhatIfSimulator metrics={metrics} />
            </ErrorBoundary>
          </div>
        </div>

        <section className="mt-6 rounded-[24px] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-base font-semibold text-[var(--color-text)]">Frame Scrubber</h2>
              <p className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">
                Frame {currentFrame + 1} of {data.total_frames} {currentFrame === data.contact_frame ? "· Contact" : ""}
              </p>
              <p className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">
                Playback starts slow so you can inspect the move without racing the frames.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setPlaying((value) => !value)}
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-text)] hover:border-[var(--color-accent)]"
                aria-label={playing ? "Pause playback" : "Play playback"}
              >
                {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              </button>
              <div className="flex items-center gap-1 rounded-lg bg-[var(--color-surface-2)] p-1">
                {PLAYBACK_SPEEDS.map((value) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setSpeed(value)}
                    className="rounded px-2.5 py-1 text-xs font-medium transition-colors"
                    style={{
                      backgroundColor: speed === value ? "var(--color-accent)" : "transparent",
                      color: speed === value ? "var(--color-bg)" : "var(--color-text-dim)",
                    }}
                  >
                    {value}x
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-5">
            <PhaseTimeline
              phaseLabels={data.phase_labels}
              totalFrames={data.total_frames}
              contactFrame={data.contact_frame}
              stridePlantFrame={data.stride_plant_frame}
              currentFrame={currentFrame}
              onFrameSelect={(frame) => {
                setPlaying(false);
                setCurrentFrame(frame);
              }}
            />
          </div>
        </section>
      </main>
    </div>
  );
}
