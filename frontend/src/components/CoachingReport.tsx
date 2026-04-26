import { Card } from "@/components/Card";
import type { CoachingLine } from "@/lib/api";

const DOT_COLOR: Record<string, string> = {
  good: "bg-[var(--color-accent)]",
  warn: "bg-[var(--color-amber)]",
  info: "bg-[var(--color-text-dim)]",
};

export function CoachingReport({ lines }: { lines: CoachingLine[] }) {
  if (!lines || lines.length === 0) {
    return (
      <Card>
        <p className="text-[var(--color-text-dim)]">No coaching report available.</p>
      </Card>
    );
  }
  return (
    <Card>
      <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
        Coaching Report
      </h3>
      <ul className="space-y-2">
        {lines.map((line, i) => (
          <li key={i} className="flex items-start gap-2 animate-fade-in-up" style={{ animationDelay: `${i * 60}ms` }}>
            <span className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${DOT_COLOR[line.tone] ?? DOT_COLOR.info}`} />
            <span className="text-sm">{line.text}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
