import type { ReactNode } from "react";
import { CheckCircle2, CircleAlert } from "lucide-react";
import { Card, CardTitle } from "@/components/Card";

interface SwingTakeawaysProps {
  strengths: string[];
  issues: string[];
}

function TakeawayList({
  title,
  icon,
  items,
  toneClass,
}: {
  title: string;
  icon: ReactNode;
  items: string[];
  toneClass: string;
}) {
  return (
    <Card className="rounded-[24px] p-6">
      <CardTitle className="mb-4 flex items-center gap-2 px-0">
        {icon}
        {title}
      </CardTitle>
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-3">
            <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${toneClass}`} />
            <p className="text-sm leading-6 text-[var(--color-text)]">{item}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function SwingTakeaways({ strengths, issues }: SwingTakeawaysProps) {
  return (
    <section aria-label="Swing takeaways" className="grid gap-6 xl:grid-cols-2">
      <TakeawayList
        title="What's working"
        icon={<CheckCircle2 className="h-4 w-4 text-[var(--color-accent)]" />}
        items={strengths}
        toneClass="bg-[var(--color-accent)]"
      />
      <TakeawayList
        title="What's costing performance"
        icon={<CircleAlert className="h-4 w-4 text-[var(--color-amber)]" />}
        items={issues}
        toneClass="bg-[var(--color-amber)]"
      />
    </section>
  );
}
