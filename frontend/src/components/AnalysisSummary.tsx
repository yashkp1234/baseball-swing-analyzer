import type { AnalysisSummary as AnalysisSummaryData } from "@/lib/api";

interface Props {
  analysis: AnalysisSummaryData | null | undefined;
}

function msToSeconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}

export function AnalysisSummary({ analysis }: Props) {
  if (!analysis) return null;

  const items = [
    { label: "Device", value: analysis.pose_device.toUpperCase() },
    { label: "Sampled Frames", value: String(analysis.sampled_frames) },
    { label: "Effective FPS", value: analysis.effective_analysis_fps.toFixed(1) },
    { label: "Runtime", value: msToSeconds(analysis.analysis_duration_ms) },
  ];

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Analysis Summary</h3>
        <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-dim)]">
          {analysis.sampling_mode}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {items.map((item) => (
          <div key={item.label} className="rounded-lg bg-[var(--color-surface-2)] px-3 py-2">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-dim)]">
              {item.label}
            </div>
            <div className="mt-1 font-mono text-sm text-[var(--color-text)]">{item.value}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-[var(--color-text-dim)]">
        <span>Source: {analysis.source_frames} frames @ {analysis.source_fps.toFixed(1)} fps</span>
        {typeof analysis.pose_inference_duration_ms === "number" && (
          <span>Pose: {msToSeconds(analysis.pose_inference_duration_ms)}</span>
        )}
      </div>
    </div>
  );
}
