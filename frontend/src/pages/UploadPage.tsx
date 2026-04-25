import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadZone } from "@/components/UploadZone";
import { ProcessingStatus } from "@/components/ProcessingStatus";
import { uploadVideo } from "@/lib/api";

export function UploadPage() {
  const navigate = useNavigate();
  const [jobId, setJobId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    setError(null);
    setIsUploading(true);
    try {
      const result = await uploadVideo(file);
      setJobId(result.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setIsUploading(false);
    }
  };

  const handleComplete = (id: string) => {
    navigate(`/results/${id}`);
  };

  const handleError = (_id: string, errMsg: string) => {
    setError(errMsg);
    setJobId(null);
    setIsUploading(false);
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

        {jobId ? (
          <ProcessingStatus
            jobId={jobId}
            onComplete={handleComplete}
            onError={handleError}
          />
        ) : (
          <UploadZone onFileSelected={handleFile} isUploading={isUploading} />
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