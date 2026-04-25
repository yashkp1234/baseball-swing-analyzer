import { type JobStatus } from "@/lib/api";

interface Props { status: JobStatus | undefined }

export function ProcessingStatus({ status }: Props) {
  const pct = Math.round((status?.progress ?? 0) * 100);
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <h2 className="text-2xl font-semibold">Analyzing swing…</h2>
        <p className="mt-2 text-sm text-[var(--color-text-dim)]">{status?.current_step ?? "queued"}</p>
        <div className="mt-6 h-2 w-full rounded-full bg-[var(--color-surface-2)] overflow-hidden">
          <div className="h-full rounded-full bg-[var(--color-accent)] transition-all" style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-1 text-xs text-[var(--color-text-dim)]">{pct}%</p>
      </div>
    </div>
  );
}
