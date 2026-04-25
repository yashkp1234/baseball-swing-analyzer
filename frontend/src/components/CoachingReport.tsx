import { Card } from "@/components/Card";

interface CoachingReportProps {
  html: string | null;
}

export function CoachingReport({ html }: CoachingReportProps) {
  if (!html) {
    return (
      <Card>
        <p className="text-[var(--color-text-dim)]">No coaching report available.</p>
      </Card>
    );
  }

  const lines = html.replace(/<\/?p>/g, "").split("\n").filter(Boolean);

  return (
    <Card>
      <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
        Coaching Report
      </h3>
      <ul className="space-y-2">
        {lines.map((line, i) => {
          const clean = line.replace(/^- /, "").trim();
          if (!clean) return null;

          const isGood =
            clean.toLowerCase().includes("good") ||
            clean.toLowerCase().includes("solid") ||
            clean.toLowerCase().includes("strong");
          const isWarn =
            clean.toLowerCase().includes("improvement") ||
            clean.toLowerCase().includes("consider") ||
            clean.toLowerCase().includes("watch") ||
            clean.toLowerCase().includes("focus");

          const dotColor = isGood
            ? "bg-[var(--color-accent)]"
            : isWarn
              ? "bg-[var(--color-amber)]"
              : "bg-[var(--color-text-dim)]";

          return (
            <li key={i} className="flex items-start gap-2 animate-fade-in-up" style={{ animationDelay: `${i * 60}ms` }}>
              <span className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${dotColor}`} />
              <span className="text-sm text-[var(--color-text)]">{clean}</span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}