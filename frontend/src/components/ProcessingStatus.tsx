import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { getJobStatus, type JobStatus } from "@/lib/api";

interface ProcessingStatusProps {
  jobId: string;
  onComplete: (jobId: string) => void;
  onError: (jobId: string, error: string) => void;
}

const STEP_LABELS: Record<string, string> = {
  queued: "Waiting in queue...",
  detecting_hitter: "Detecting hitter...",
  computing_metrics: "Computing biomechanical metrics...",
  generating_coaching: "Generating coaching report...",
  generating_3d_data: "Preparing 3D visualization data...",
  done: "Analysis complete!",
};

export function ProcessingStatus({ jobId, onComplete, onError }: ProcessingStatusProps) {
  const [status, setStatus] = useState<JobStatus | null>(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const s = await getJobStatus(jobId);
        setStatus(s);
        if (s.status === "completed") {
          clearInterval(interval);
          onComplete(jobId);
        } else if (s.status === "failed") {
          clearInterval(interval);
          onError(jobId, s.error_message || "Analysis failed");
        }
      } catch {
        // keep polling on transient errors
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [jobId, onComplete, onError]);

  const progress = status?.progress ?? 0;
  const step = status?.current_step ?? "queued";
  const label = STEP_LABELS[step] || step;

  return (
    <div className="flex flex-col items-center gap-4 py-8">
      <Loader2 className="h-8 w-8 animate-spin text-[var(--color-accent)]" />
      <p className="text-[var(--color-text)] font-medium">{label}</p>
      <div className="w-full max-w-md h-2 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
        <div
          className="h-full rounded-full bg-[var(--color-accent)] transition-all duration-500"
          style={{ width: `${Math.max(progress * 100, 5)}%` }}
        />
      </div>
      <p className="text-xs text-[var(--color-text-dim)]">Job ID: {jobId.slice(0, 8)}...</p>
    </div>
  );
}