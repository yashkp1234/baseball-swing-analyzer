import { metricZone, formatMetric } from "@/lib/metrics";
import { cn } from "@/lib/utils";
import { Card } from "@/components/Card";

interface MetricCardProps {
  label: string;
  value: number | string;
  metricKey?: string;
  className?: string;
}

export function MetricCard({ label, value, metricKey, className }: MetricCardProps) {
  const numericValue = typeof value === "number" ? value : parseFloat(String(value));
  const zone = metricKey && !isNaN(numericValue) ? metricZone(metricKey, numericValue) : "moderate";

  const borderColors: Record<string, string> = {
    good: "border-l-[var(--color-accent)]",
    moderate: "border-l-[var(--color-amber)]",
    poor: "border-l-[var(--color-red)]",
  };

  const valueColors: Record<string, string> = {
    good: "text-[var(--color-accent)]",
    moderate: "text-[var(--color-amber)]",
    poor: "text-[var(--color-red)]",
  };

  return (
    <Card className={cn("border-l-4", borderColors[zone], className)}>
      <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-dim)] mb-1">
        {label.replace(/_/g, " ")}
      </p>
      <p className={cn("text-2xl font-bold", valueColors[zone])}>
        {metricKey ? formatMetric(metricKey, value) : String(value)}
      </p>
    </Card>
  );
}