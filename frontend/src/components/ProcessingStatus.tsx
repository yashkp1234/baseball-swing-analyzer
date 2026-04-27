import { type JobStatus } from "@/lib/api";

interface Props {
  status: JobStatus | undefined;
}

const STEP_LABELS: Record<string, { title: string; detail: string }> = {
  queued: {
    title: "Queueing your clip",
    detail: "We are reserving a processing slot for the upload.",
  },
  loading_video: {
    title: "Loading your video",
    detail: "Checking the clip, frame rate, and timing window.",
  },
  sampling: {
    title: "Planning the frame pass",
    detail: "Choosing the parts of the clip that matter most for the swing.",
  },
  pose_inference: {
    title: "Detecting your body positions",
    detail: "Tracking the body frame by frame to build the swing model.",
  },
  computing_metrics: {
    title: "Measuring the swing",
    detail: "Calculating timing, rotation, posture, and movement quality.",
  },
  generating_coaching: {
    title: "Writing the report",
    detail: "Turning the raw measurements into player-facing coaching notes.",
  },
  generating_3d_data: {
    title: "Building the breakdown view",
    detail: "Preparing the frame scrubber, phase data, and swing breakdown panels.",
  },
  finalizing: {
    title: "Finalizing results",
    detail: "Saving the analysis and getting the report ready to open.",
  },
  done: {
    title: "Done",
    detail: "Your report is ready.",
  },
};

export function ProcessingStatus({ status }: Props) {
  const pct = Math.round((status?.progress ?? 0) * 100);
  const stepKey = status?.current_step ?? "queued";
  const step = STEP_LABELS[stepKey] ?? {
    title: stepKey.replaceAll("_", " "),
    detail: "Processing your swing.",
  };

  const detailCurrent = status?.progress_detail_current;
  const detailTotal = status?.progress_detail_total;
  const detailLabel = status?.progress_detail_label ?? "frames";
  const progressDetail =
    typeof detailCurrent === "number" && typeof detailTotal === "number"
      ? `${detailCurrent} / ${detailTotal} ${detailLabel}`
      : "Setting up the pipeline";

  const orderedSteps = [
    "queued",
    "loading_video",
    "sampling",
    "pose_inference",
    "computing_metrics",
    "generating_coaching",
    "generating_3d_data",
    "finalizing",
    "done",
  ];
  const activeIndex = Math.max(orderedSteps.indexOf(stepKey), 0);

  return (
    <div className="min-h-screen bg-[var(--color-bg)] px-5 py-10 lg:px-8">
      <div className="mx-auto grid max-w-[1280px] gap-8 lg:grid-cols-[minmax(0,1.1fr)_420px]">
        <section className="rounded-[32px] border border-white/10 bg-[linear-gradient(135deg,rgba(13,18,28,0.98),rgba(22,28,38,0.94))] p-8 shadow-[0_24px_80px_rgba(0,0,0,0.28)] lg:p-10">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[var(--color-accent)]">Swing analysis in progress</p>
          <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-[var(--color-text)] lg:text-6xl">
            {step.title}
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--color-text-dim)] lg:text-lg">
            {step.detail}
          </p>

          <div className="mt-8 rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.03)] p-5">
            <div className="flex items-center justify-between text-sm text-[var(--color-text-dim)]">
              <span>Progress</span>
              <span>{pct}%</span>
            </div>
            <div className="mt-3 h-3 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
              <div
                className="h-full rounded-full bg-[var(--color-accent)] transition-all duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="mt-3 text-sm text-[var(--color-text-dim)]">{progressDetail}</p>
          </div>
        </section>

        <aside className="rounded-[32px] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 lg:p-7">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-text-dim)]">Pipeline steps</p>
          <div className="mt-5 space-y-4">
            {orderedSteps.slice(0, -1).map((key, index) => {
              const isDone = index < activeIndex;
              const isActive = key === stepKey;
              const label = STEP_LABELS[key];
              return (
                <div key={key} className="flex items-start gap-3">
                  <div
                    className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-full border text-xs font-semibold"
                    style={{
                      borderColor: isActive || isDone ? "var(--color-accent)" : "var(--color-border)",
                      backgroundColor: isActive ? "var(--color-accent)" : isDone ? "rgba(0,255,135,0.12)" : "transparent",
                      color: isActive ? "var(--color-bg)" : isDone ? "var(--color-accent)" : "var(--color-text-dim)",
                    }}
                  >
                    {index + 1}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[var(--color-text)]">{label.title}</p>
                    <p className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">{label.detail}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </aside>
      </div>
    </div>
  );
}
