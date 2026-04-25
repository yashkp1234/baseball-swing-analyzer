import { cn } from "@/lib/utils";

interface FlagBadgeProps {
  label: string;
  value: string | boolean;
  type?: "good" | "warn" | "info";
}

export function FlagBadge({ label, value, type }: FlagBadgeProps) {
  const boolVal = typeof value === "boolean" ? value : null;
  const strVal = typeof value === "string" ? value : value ? "Yes" : "No";

  const inferred = type ?? (boolVal === true ? "good" : boolVal === false ? "warn" : "info");

  const colors: Record<string, string> = {
    good: "bg-[var(--color-accent)]/15 text-[var(--color-accent)] border-[var(--color-accent)]/30",
    warn: "bg-[var(--color-amber)]/15 text-[var(--color-amber)] border-[var(--color-amber)]/30",
    info: "bg-[var(--color-surface-2)] text-[var(--color-text-dim)] border-[var(--color-border)]",
  };

  const icon = inferred === "good" ? "✓" : inferred === "warn" ? "⚠" : null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
        colors[inferred]
      )}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{label}: {strVal}</span>
    </span>
  );
}

interface FlagsPanelProps {
  flags: {
    handedness: string;
    front_shoulder_closed_load: boolean;
    leg_action: string;
    finish_height: string;
    hip_casting: boolean;
    arm_slot_at_contact: string;
  };
}

export function FlagsPanel({ flags }: FlagsPanelProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <FlagBadge label="Handedness" value={flags.handedness} type="info" />
      <FlagBadge
        label="Shoulder"
        value={flags.front_shoulder_closed_load}
        type={flags.front_shoulder_closed_load ? "good" : "warn"}
      />
      <FlagBadge label="Leg action" value={flags.leg_action} type="info" />
      <FlagBadge
        label="Finish"
        value={flags.finish_height}
        type={flags.finish_height === "high" ? "good" : "warn"}
      />
      <FlagBadge
        label="Hip casting"
        value={flags.hip_casting}
        type={flags.hip_casting ? "warn" : "good"}
      />
      <FlagBadge label="Arm slot" value={flags.arm_slot_at_contact} type="info" />
    </div>
  );
}
