interface PhaseConfidenceBannerProps {
  isCurrentAnalysis?: boolean;
  analysisVersion?: string | null;
  measurementReliability?: "normal" | "low" | null;
}

export function PhaseConfidenceBanner({
  isCurrentAnalysis = true,
  analysisVersion,
  measurementReliability,
}: PhaseConfidenceBannerProps) {
  const messages: string[] = [];

  if (!isCurrentAnalysis) {
    messages.push(
      `This result was generated with an older analysis pass${analysisVersion ? ` (${analysisVersion})` : ""}. Re-run the clip before trusting swing counts or cut points.`,
    );
  }

  if (measurementReliability === "low") {
    messages.push("Pose confidence is low on this clip, so phase timing and some movement metrics may be approximate.");
  }

  if (messages.length === 0) return null;

  return (
    <section className="rounded-[20px] border border-[var(--color-amber)]/30 bg-[var(--color-amber)]/10 px-4 py-3 text-sm leading-6 text-[var(--color-text)]">
      {messages.map((message) => (
        <p key={message}>{message}</p>
      ))}
    </section>
  );
}
