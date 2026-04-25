import { ChevronDown, Gauge, Microscope } from "lucide-react";
import { AnalysisSummary } from "@/components/AnalysisSummary";
import { Card, CardTitle } from "@/components/Card";
import { MetricCard } from "@/components/MetricCard";
import { PhaseTimeline } from "@/components/PhaseTimeline";
import type { AnalysisSummary as AnalysisSummaryData, SwingMetrics } from "@/lib/api";

interface DiagnosticMetricDefinition {
  key: keyof SwingMetrics;
  label: string;
}

interface DetailsDiagnosticsProps {
  analysis: AnalysisSummaryData | null | undefined;
  metrics: SwingMetrics;
  metricDefinitions: DiagnosticMetricDefinition[];
  currentFrame?: number;
  onFrameSelect?: (frame: number) => void;
}

export function DetailsDiagnostics({ analysis, metrics, metricDefinitions, currentFrame, onFrameSelect }: DetailsDiagnosticsProps) {
  return (
    <section
      aria-label="Details and diagnostics"
      className="rounded-[24px] border border-[var(--color-border)] bg-[linear-gradient(180deg,rgba(15,20,30,0.82),rgba(10,14,22,0.94))] shadow-[0_18px_48px_rgba(0,0,0,0.16)]"
    >
      <details className="group" open={false}>
        <summary className="list-none cursor-pointer px-5 py-4 md:px-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="max-w-2xl">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
                <Microscope className="h-3.5 w-3.5" />
                Details and diagnostics
              </div>
              <p className="mt-2 text-sm leading-6 text-[var(--color-text-dim)]">
                Secondary review surface for metadata, raw measurements, and phase timing when you need to inspect the
                analysis behind the summary.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 rounded-full border border-white/8 bg-white/4 px-3 py-1.5 text-[11px] font-medium text-[var(--color-text-dim)] sm:inline-flex">
                <Gauge className="h-3.5 w-3.5" />
                {metricDefinitions.length} reference metrics
              </div>
              <div className="rounded-full border border-white/8 bg-white/4 p-2 text-[var(--color-text-dim)] transition group-open:rotate-180">
                <ChevronDown className="h-4 w-4" />
              </div>
            </div>
          </div>
        </summary>

        <div className="space-y-5 border-t border-white/8 px-5 py-5 md:px-6">
          <AnalysisSummary analysis={analysis} />

          <Card className="rounded-[20px] bg-[var(--color-surface)]/72">
            <CardTitle>Phase Timeline</CardTitle>
            <p className="mb-3 text-sm leading-6 text-[var(--color-text-dim)]">
              Select a phase to jump the annotated video.
            </p>
            <PhaseTimeline
              phaseLabels={metrics.phase_labels}
              phaseDurations={metrics.phase_durations}
              totalFrames={metrics.frames}
              stridePlantFrame={metrics.stride_plant_frame}
              contactFrame={metrics.contact_frame}
              currentFrame={currentFrame}
              onFrameSelect={onFrameSelect}
            />
            <div className="mt-2 flex flex-wrap gap-4 text-xs text-[var(--color-text-dim)]">
              <span>Stride plant: frame {metrics.stride_plant_frame ?? "-"}</span>
              <span>Contact: frame {metrics.contact_frame}</span>
              <span>Total: {metrics.frames} frames @ {metrics.fps.toFixed(1)} fps</span>
              <span>Pose confidence: {(metrics.pose_confidence_mean * 100).toFixed(0)}%</span>
            </div>
          </Card>

          <Card className="rounded-[20px] bg-[var(--color-surface)]/72 p-5">
            <div className="mb-4 flex flex-col gap-2 px-1 md:flex-row md:items-end md:justify-between">
              <div>
                <CardTitle className="mb-1 px-0">Supporting metrics</CardTitle>
                <p className="max-w-3xl text-sm leading-6 text-[var(--color-text-dim)]">
                  Reference numbers for coach-level inspection after the summary, video, and next-step recommendations.
                </p>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              {metricDefinitions.map(({ key, label }) => {
                const value = metrics[key];

                return (
                  <MetricCard
                    key={key as string}
                    label={label}
                    value={typeof value === "number" ? value : String(value)}
                    metricKey={key as string}
                    className="bg-[var(--color-surface-2)]/35 p-4"
                  />
                );
              })}
            </div>
          </Card>
        </div>
      </details>
    </section>
  );
}
