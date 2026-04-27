import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadZone } from "@/components/UploadZone";
import { uploadVideo } from "@/lib/api";

const PREVIEW_PANELS = [
  {
    title: "Body turn",
    body: "See how the hips and shoulders moved into contact.",
  },
  {
    title: "Power flow",
    body: "Spot where the swing built speed and where it leaked.",
  },
  {
    title: "What to fix",
    body: "Test cleaner movement targets before the next round of swings.",
  },
];

export function UploadPage() {
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    setError(null);
    setIsUploading(true);
    try {
      const { job_id } = await uploadVideo(file);
      navigate(`/results/${job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)] px-5 py-10 lg:px-8">
      <div className="mx-auto grid max-w-[1380px] gap-10 lg:grid-cols-[minmax(0,1.1fr)_520px] lg:items-center">
        <section>
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[var(--color-accent)]">Swing breakdown in under 30 seconds</p>
          <h1 className="mt-4 max-w-4xl text-5xl font-semibold tracking-tight text-[var(--color-text)] lg:text-7xl">
            Upload your swing video. Get a clear, player-friendly breakdown fast.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[var(--color-text-dim)]">
            We turn one swing clip into timing, rotation, and movement feedback that is easier to act on than a wall of raw metrics.
          </p>

          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {PREVIEW_PANELS.map((panel, index) => (
              <div
                key={panel.title}
                className="rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,20,30,0.82),rgba(10,14,22,0.94))] p-5 shadow-[0_18px_48px_rgba(0,0,0,0.16)]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-accent)]/12 text-sm font-semibold text-[var(--color-accent)]">
                  {index + 1}
                </div>
                <p className="mt-4 text-base font-semibold text-[var(--color-text)]">{panel.title}</p>
                <p className="mt-2 text-sm leading-6 text-[var(--color-text-dim)]">{panel.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <UploadZone onFileSelected={handleFile} isUploading={isUploading} />
          {error ? (
            <div className="mt-4 rounded-xl border border-[var(--color-red)] bg-[var(--color-red)]/10 p-4 text-sm text-[var(--color-red)]">
              {error}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
