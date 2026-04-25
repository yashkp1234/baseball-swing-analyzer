import { Link } from "react-router-dom";
import { useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export function SwingViewerPage() {
  const { jobId } = useParams<{ jobId: string }>();

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex flex-col">
      <header className="border-b border-[var(--color-border)] px-6 py-3 flex items-center justify-between">
        <Link
          to={jobId ? `/results/${jobId}` : "/"}
          className="flex items-center gap-2 text-[var(--color-text-dim)] hover:text-[var(--color-text)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">Back to Results</span>
        </Link>
        <h1 className="text-lg font-semibold">
          Swing <span className="text-[var(--color-accent)]">Breakdown</span>
        </h1>
        <div className="w-32" />
      </header>

      <div className="flex-1 flex items-center justify-center">
        <p className="text-[var(--color-text-dim)] text-sm">Building Swing Breakdown…</p>
      </div>
    </div>
  );
}
