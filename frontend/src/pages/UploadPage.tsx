import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadZone } from "@/components/UploadZone";
import { uploadAndAnalyze, type AnalysisResponse } from "@/lib/api";

export function UploadPage() {
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    setError(null);
    setIsUploading(true);
    try {
      const result = await uploadAndAnalyze(file);
      if (result.status === "failed") {
        setError(result.error || "Analysis failed");
        setIsUploading(false);
        return;
      }
      sessionStorage.setItem(`result_${result.job_id}`, JSON.stringify(result));
      navigate(`/results/${result.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-xl">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold tracking-tight text-[var(--color-text)]">
            Swing<span className="text-[var(--color-accent)]">Metrics</span>
          </h1>
          <p className="mt-2 text-[var(--color-text-dim)]">
            Upload a baseball swing video for biomechanical analysis
          </p>
        </div>

        <UploadZone onFileSelected={handleFile} isUploading={isUploading} />

        {isUploading && (
          <div className="mt-6 flex flex-col items-center gap-2">
            <div className="h-2 w-full max-w-md rounded-full bg-[var(--color-surface-2)] overflow-hidden">
              <div className="h-full rounded-full bg-[var(--color-accent)] animate-pulse" style={{ width: "60%" }} />
            </div>
            <p className="text-sm text-[var(--color-text-dim)]">Analyzing swing — this takes 10-30 seconds...</p>
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-lg border border-[var(--color-red)] bg-[var(--color-red)]/10 p-3 text-sm text-[var(--color-red)]">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}