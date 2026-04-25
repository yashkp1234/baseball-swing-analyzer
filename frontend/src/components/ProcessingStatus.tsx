import { type JobStatus } from "@/lib/api";

interface Props {
  status: JobStatus | undefined;
}

const STEP_LABELS: Record<string, string> = {
  queued: "Queued",
  loading_video: "Loading video",
  sampling: "Planning frame sampling",
  pose_inference: "Analyzing frames",
  computing_metrics: "Computing metrics",
  generating_coaching: "Generating coaching notes",
  generating_3d_data: "Preparing 3D swing data",
  finalizing: "Finalizing results",
  done: "Done",
};

export function ProcessingStatus({ status }: Props) {
  const pct = Math.round((status?.progress ?? 0) * 100);
  const stepKey = status?.current_step ?? "queued";
  const stepLabel = STEP_LABELS[stepKey] ?? stepKey.replaceAll("_", " ");
  const detailCurrent = status?.progress_detail_current;
  const detailTotal = status?.progress_detail_total;
  const detailLabel = status?.progress_detail_label ?? "items";
  const detailText =
    typeof detailCurrent === "number" && typeof detailTotal === "number"
      ? `${detailCurrent} / ${detailTotal} ${detailLabel}`
      : "Preparing analysis pipeline";

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-lg text-center">
        <h2 className="text-2xl font-semibold">Analyzing swing...</h2>
        <p className="mt-2 text-sm text-[var(--color-text-dim)]">{stepLabel}</p>
        <div className="mt-6 h-3 w-full overflow-hidden rounded-full bg-[var(--color-surface-2)]">
          <div
            className="h-full rounded-full bg-[var(--color-accent)] transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-[var(--color-text-dim)]">
          <span>{pct}%</span>
          <span>{detailText}</span>
        </div>
      </div>
    </div>
  );
}
