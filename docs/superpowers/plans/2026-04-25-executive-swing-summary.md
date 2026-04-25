# Executive Swing Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the results page into an executive swing summary that leads with score, strengths, issues, next steps, and annotated-video proof while moving diagnostics into a secondary details area.

**Architecture:** Keep backend analysis unchanged and do the redesign as a presentation-layer refactor in the frontend. Add lightweight summary-mapping helpers, replace metadata-first top sections with an editorial page structure, and move raw metrics plus processing data into a lower-priority diagnostics area with an interactive timeline.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind CSS v4 utilities, lucide-react, TanStack Query

---

## File Structure

- Modify: `frontend/src/pages/ResultsPage.tsx`
  - Recompose the page around hero summary, evidence video, coaching sections, and details.
- Modify: `frontend/src/components/AnalysisSummary.tsx`
  - Either replace with executive-summary behavior or reduce it to a diagnostics presenter.
- Modify: `frontend/src/components/PhaseTimeline.tsx`
  - Add hover/focus/click interactions and event markers.
- Modify: `frontend/src/components/VideoPlayer.tsx`
  - Expose a video ref or seek API that timeline interactions can target.
- Modify: `frontend/src/components/FlagsPanel.tsx`
  - Convert flags from badge dump into source material for narrative takeaways.
- Modify: `frontend/src/components/CoachingReport.tsx`
  - Convert freeform report styling into ordered action-oriented presentation.
- Modify: `frontend/src/components/MetricCard.tsx`
  - Reduce visual weight for details-area use.
- Modify: `frontend/src/index.css`
  - Refine global type, spacing, section, and interaction tokens as needed.
- Create: `frontend/src/lib/resultsSummary.ts`
  - Derive score band, executive summary copy, strengths, issues, and next actions from existing metrics, flags, and coaching lines.
- Create: `frontend/src/components/ExecutiveSummaryHero.tsx`
  - Render score, label, one-sentence summary, and proof-oriented framing.
- Create: `frontend/src/components/SwingTakeaways.tsx`
  - Render strengths and issues sections with consistent iconography and hierarchy.
- Create: `frontend/src/components/ImprovementPlan.tsx`
  - Render the prioritized next actions block.
- Create: `frontend/src/components/DetailsDiagnostics.tsx`
- Create: `scripts/verify_results_page.py`
  - Render secondary metadata, raw metrics, and timeline in a demoted section.

## Milestone 1 Success Criteria

- The top viewport shows score, executive summary, and annotated video.
- Device/runtime/sampling data is removed from the top summary surface.
- Results page data fetching and error handling continue to work unchanged.

### Task 1: Executive Summary Skeleton

**Files:**
- Create: `frontend/src/lib/resultsSummary.ts`
- Create: `frontend/src/components/ExecutiveSummaryHero.tsx`
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/components/AnalysisSummary.tsx`

- [ ] **Step 1: Add the summary mapping helper**

```ts
import type { CoachingLine, SwingMetrics } from "@/lib/api";
import { metricZone } from "@/lib/metrics";

export interface ExecutiveSummaryModel {
  score: number;
  label: string;
  summary: string;
  strengths: string[];
  issues: string[];
  nextSteps: string[];
}

export function buildExecutiveSummary(
  metrics: SwingMetrics,
  coaching: CoachingLine[] | null | undefined,
): ExecutiveSummaryModel {
  const scoredMetrics: Array<keyof SwingMetrics> = [
    "x_factor_at_contact",
    "hip_angle_at_contact",
    "shoulder_angle_at_contact",
    "spine_tilt_at_contact",
    "left_knee_at_contact",
    "right_knee_at_contact",
    "head_displacement_total",
    "wrist_peak_velocity_normalized",
  ];

  const points = scoredMetrics.reduce((total, key) => {
    const value = metrics[key];
    if (typeof value !== "number") return total;
    const zone = metricZone(String(key), value);
    return total + (zone === "good" ? 12 : zone === "moderate" ? 8 : 4);
  }, 0);

  const score = Math.max(40, Math.min(99, points));
  const label = score >= 85 ? "Game-ready foundation" : score >= 70 ? "Promising swing" : "Needs cleanup";

  return {
    score,
    label,
    summary: `This swing shows ${label.toLowerCase()} with the biggest gains coming from the first correction in the action plan.`,
    strengths: [],
    issues: [],
    nextSteps: [],
  };
}
```

- [ ] **Step 2: Add the hero component**

```tsx
import { Activity, Medal, Radar } from "lucide-react";
import type { ExecutiveSummaryModel } from "@/lib/resultsSummary";

export function ExecutiveSummaryHero({ summary }: { summary: ExecutiveSummaryModel }) {
  return (
    <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 lg:p-8">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1 text-xs uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
            <Radar className="h-3.5 w-3.5" />
            Executive Summary
          </div>
          <div>
            <p className="text-5xl font-semibold leading-none">{summary.score}</p>
            <h2 className="mt-3 text-2xl font-semibold">{summary.label}</h2>
            <p className="mt-2 max-w-2xl text-sm text-[var(--color-text-dim)]">{summary.summary}</p>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
              <Medal className="h-4 w-4" />
              Score Signal
            </div>
            <p className="mt-3 text-sm text-[var(--color-text)]">Built from the current biomechanical metrics already returned by the analysis API.</p>
          </div>
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
              <Activity className="h-4 w-4" />
              Proof
            </div>
            <p className="mt-3 text-sm text-[var(--color-text)]">Use the annotated video below to verify that the written summary matches the actual swing.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Recompose the results page around the hero and video**

```tsx
const executiveSummary = buildExecutiveSummary(m, resultsQuery.data?.coaching);

return (
  <div className="min-h-screen bg-[var(--color-bg)]">
    <header>{/* keep existing nav shell */}</header>
    <main className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-6 lg:px-6 lg:py-8">
      <ExecutiveSummaryHero summary={executiveSummary} />

      <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <Card className="overflow-hidden p-4 lg:p-5">
          <CardTitle className="mb-2">Annotated Video</CardTitle>
          <p className="mb-4 text-sm text-[var(--color-text-dim)]">
            This is the evidence layer for the report. Use it to confirm the summary against the actual swing.
          </p>
          <VideoPlayer src={videoSrc} />
        </Card>
        <AnalysisSummary analysis={resultsQuery.data?.analysis} />
      </section>
    </main>
  </div>
);
```

- [ ] **Step 4: Demote `AnalysisSummary` into diagnostics content**

```tsx
export function AnalysisSummary({ analysis }: Props) {
  if (!analysis) return null;

  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h3 className="text-sm font-semibold text-[var(--color-text)]">Analysis details</h3>
      <p className="mt-1 text-sm text-[var(--color-text-dim)]">
        Processing transparency for advanced review.
      </p>
      {/* keep metadata grid here for now; it moves fully into DetailsDiagnostics in Milestone 3 */}
    </div>
  );
}
```

- [ ] **Step 5: Verify the page still builds**

Run: `npm run build`

Expected: Vite production build completes successfully with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/resultsSummary.ts frontend/src/components/ExecutiveSummaryHero.tsx frontend/src/pages/ResultsPage.tsx frontend/src/components/AnalysisSummary.tsx
git commit -m "feat: add executive summary hero to results page"
```

## Milestone 2 Success Criteria

- The main flow clearly separates what is good, what is hurting performance, and what to improve next.
- A user can understand the story of the swing without reading raw metric cards.
- The annotated video remains visually prominent.

### Task 2: Coaching Narrative Sections

**Files:**
- Create: `frontend/src/components/SwingTakeaways.tsx`
- Create: `frontend/src/components/ImprovementPlan.tsx`
- Modify: `frontend/src/lib/resultsSummary.ts`
- Modify: `frontend/src/components/FlagsPanel.tsx`
- Modify: `frontend/src/components/CoachingReport.tsx`
- Modify: `frontend/src/pages/ResultsPage.tsx`

- [ ] **Step 1: Expand the summary helper to derive strengths, issues, and next steps**

```ts
function pickStrengths(metrics: SwingMetrics): string[] {
  const strengths: string[] = [];
  if (metrics.flags.hip_casting === false) strengths.push("Hip rotation stays connected instead of leaking early.");
  if (metrics.flags.front_shoulder_closed_load) strengths.push("Front shoulder stays closed through the load, which helps preserve stretch.");
  if (metrics.head_displacement_total <= 30) strengths.push("Head movement stays controlled, giving the swing a stable base.");
  return strengths.slice(0, 3);
}

function pickIssues(metrics: SwingMetrics): string[] {
  const issues: string[] = [];
  if (metrics.flags.finish_height !== "high") issues.push("The finish is cut off, which can cost extension through contact.");
  if (metrics.left_knee_at_contact < 15) issues.push("Lead leg is too straight at contact, reducing leverage.");
  if (metrics.x_factor_at_contact < 15) issues.push("Hip-shoulder separation is limited, so stored rotational energy is low.");
  return issues.slice(0, 3);
}

function pickNextSteps(coaching: CoachingLine[] | null | undefined): string[] {
  return (coaching ?? []).map((line) => line.text).slice(0, 4);
}
```

- [ ] **Step 2: Add the strengths/issues presenter**

```tsx
import { AlertTriangle, CheckCircle2 } from "lucide-react";

interface SwingTakeawaysProps {
  strengths: string[];
  issues: string[];
}

export function SwingTakeaways({ strengths, issues }: SwingTakeawaysProps) {
  return (
    <section className="grid gap-6 xl:grid-cols-2">
      <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text)]">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          What's working
        </div>
        <ul className="mt-4 space-y-3 text-sm text-[var(--color-text-dim)]">
          {strengths.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </div>
      <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text)]">
          <AlertTriangle className="h-4 w-4 text-amber-400" />
          What's costing performance
        </div>
        <ul className="mt-4 space-y-3 text-sm text-[var(--color-text-dim)]">
          {issues.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Add the improvement plan block**

```tsx
import { ArrowRight, Target } from "lucide-react";

export function ImprovementPlan({ nextSteps }: { nextSteps: string[] }) {
  return (
    <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text)]">
        <Target className="h-4 w-4 text-[var(--color-accent)]" />
        What to improve next
      </div>
      <ol className="mt-4 space-y-3">
        {nextSteps.map((step, index) => (
          <li key={step} className="flex gap-3 rounded-2xl bg-[var(--color-surface-2)] p-4">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent)]/15 text-sm font-semibold text-[var(--color-accent)]">
              {index + 1}
            </span>
            <div className="flex-1">
              <p className="text-sm text-[var(--color-text)]">{step}</p>
              {index === 0 && (
                <div className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-[var(--color-accent)]">
                  Highest-impact fix <ArrowRight className="h-3.5 w-3.5" />
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
```

- [ ] **Step 4: Replace widget-style sections in `ResultsPage`**

```tsx
<section className="flex flex-col gap-6">
  <SwingTakeaways strengths={executiveSummary.strengths} issues={executiveSummary.issues} />
  <ImprovementPlan nextSteps={executiveSummary.nextSteps} />
</section>
```

- [ ] **Step 5: Keep old components as compatibility wrappers or remove their use**

```tsx
export function CoachingReport({ lines }: { lines: CoachingLine[] }) {
  return <ImprovementPlan nextSteps={lines.map((line) => line.text)} />;
}
```

- [ ] **Step 6: Verify lint and build**

Run: `npm run lint`
Expected: ESLint exits cleanly.

Run: `npm run build`
Expected: Production build succeeds after the new components are wired in.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/SwingTakeaways.tsx frontend/src/components/ImprovementPlan.tsx frontend/src/lib/resultsSummary.ts frontend/src/components/FlagsPanel.tsx frontend/src/components/CoachingReport.tsx frontend/src/pages/ResultsPage.tsx
git commit -m "feat: add executive swing takeaways and action plan"
```

## Milestone 3 Success Criteria

- Metadata, raw metrics, and advanced inspection elements move into a clearly secondary area.
- The page retains transparency without reading like a dashboard.
- Raw metric cards no longer dominate the main flow.

### Task 3: Details And Diagnostics Section

**Files:**
- Create: `frontend/src/components/DetailsDiagnostics.tsx`
- Modify: `frontend/src/components/AnalysisSummary.tsx`
- Modify: `frontend/src/components/MetricCard.tsx`
- Modify: `frontend/src/pages/ResultsPage.tsx`

- [ ] **Step 1: Add the details shell**

```tsx
import type { AnalysisSummary, SwingMetrics } from "@/lib/api";
import { ChevronDown, ChevronUp, Gauge, Rows3 } from "lucide-react";
import { useState } from "react";

export function DetailsDiagnostics({
  analysis,
  metrics,
  children,
}: {
  analysis: AnalysisSummary | null | undefined;
  metrics: SwingMetrics;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between text-left"
      >
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text)]">
            <Gauge className="h-4 w-4 text-[var(--color-text-dim)]" />
            Details and diagnostics
          </div>
          <p className="mt-1 text-sm text-[var(--color-text-dim)]">
            Advanced metrics, processing metadata, and swing-phase inspection.
          </p>
        </div>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && <div className="mt-5 space-y-5">{children}</div>}
    </section>
  );
}
```

- [ ] **Step 2: Move metadata and metric cards into the details section**

```tsx
<DetailsDiagnostics analysis={resultsQuery.data?.analysis} metrics={m}>
  <AnalysisSummary analysis={resultsQuery.data?.analysis} />
  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
    {DISPLAY_METRICS.map(({ key, label }) => {
      const val = m[key];
      return (
        <MetricCard
          key={key as string}
          label={label}
          value={typeof val === "number" ? val : String(val)}
          metricKey={key as string}
          className="bg-[var(--color-surface-2)]"
        />
      );
    })}
  </div>
  {/* timeline goes here in Task 4 */}
</DetailsDiagnostics>
```

- [ ] **Step 3: Make metric cards quieter**

```tsx
return (
  <Card className={cn("border-l-4 bg-[var(--color-surface-2)] p-4", borderColors[zone], className)}>
    <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
      {label.replace(/_/g, " ")}
    </p>
    <p className={cn("mt-2 text-xl font-semibold", valueColors[zone])}>
      {metricKey ? formatMetric(metricKey, value) : String(value)}
    </p>
  </Card>
);
```

- [ ] **Step 4: Verify the main page is still executive-first**

Run: `npm run build`

Expected: Build succeeds and the details container compiles without prop/type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DetailsDiagnostics.tsx frontend/src/components/AnalysisSummary.tsx frontend/src/components/MetricCard.tsx frontend/src/pages/ResultsPage.tsx
git commit -m "feat: move swing diagnostics into secondary details section"
```

## Milestone 4 Success Criteria

- Timeline interaction is useful on hover, keyboard focus, and click.
- Important swing events are visible and understandable.
- The final page feels polished and cohesive on desktop and mobile.

### Task 4: Interactive Timeline And Final UI Polish

**Files:**
- Modify: `frontend/src/components/PhaseTimeline.tsx`
- Modify: `frontend/src/components/VideoPlayer.tsx`
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Expose a seek API from `VideoPlayer`**

```tsx
import { forwardRef, useImperativeHandle, useRef } from "react";

export interface VideoPlayerHandle {
  seekToSeconds: (seconds: number) => void;
}

export const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(function VideoPlayer(
  { src, className },
  ref,
) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useImperativeHandle(ref, () => ({
    seekToSeconds(seconds: number) {
      if (videoRef.current) videoRef.current.currentTime = seconds;
    },
  }));

  return <video ref={videoRef} src={src} controls className={`w-full rounded-lg bg-black ${className ?? ""}`} style={{ maxHeight: "480px" }} />;
});
```

- [ ] **Step 2: Make the timeline interactive and event-aware**

```tsx
interface PhaseTimelineProps {
  phaseLabels: string[];
  fps: number;
  stridePlantFrame?: number | null;
  contactFrame?: number | null;
  currentFrame?: number;
  selectedFrame?: number | null;
  onFrameSelect?: (frame: number) => void;
}

<button
  type="button"
  key={`${seg.phase}-${idx}`}
  className="group relative h-10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
  style={{ width: `${(seg.width / total) * 100}%`, backgroundColor: PHASE_COLORS[seg.phase] || "#555" }}
  onClick={() => onFrameSelect?.(seg.start)}
  onFocus={() => setActiveSegment(idx)}
  onMouseEnter={() => setActiveSegment(idx)}
>
  <span className="sr-only">{`${seg.phase} from frame ${seg.start} to ${seg.start + seg.width - 1}`}</span>
  <span className="pointer-events-none absolute left-1/2 top-full z-10 mt-2 hidden w-48 -translate-x-1/2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-left text-xs text-[var(--color-text)] group-hover:block group-focus:block">
    <strong className="block text-sm">{seg.phase}</strong>
    <span className="block text-[var(--color-text-dim)]">Frames {seg.start}-{seg.start + seg.width - 1}</span>
    <span className="mt-2 block text-[var(--color-text-dim)]">{PHASE_EXPLANATIONS[seg.phase] ?? "Swing phase"}</span>
  </span>
</button>
```

- [ ] **Step 3: Wire timeline clicks to the video**

```tsx
const videoRef = useRef<VideoPlayerHandle>(null);
const [selectedFrame, setSelectedFrame] = useState<number | null>(null);

function handleFrameSelect(frame: number) {
  setSelectedFrame(frame);
  videoRef.current?.seekToSeconds(frame / m.fps);
}

<VideoPlayer ref={videoRef} src={videoSrc} />
<PhaseTimeline
  phaseLabels={m.phase_labels}
  fps={m.fps}
  stridePlantFrame={m.stride_plant_frame}
  contactFrame={m.contact_frame}
  selectedFrame={selectedFrame}
  onFrameSelect={handleFrameSelect}
/>
```

- [ ] **Step 4: Polish global section styling**

```css
.section-eyebrow {
  color: var(--color-text-dim);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.panel-glow {
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
}
```

- [ ] **Step 5: Verify lint, build, and browser behavior**

Run: `npm run lint`
Expected: ESLint exits with code 0.

Run: `npm run build`
Expected: Vite build succeeds and emits the production bundle.

Run: `python scripts/with_server.py --server "npm run dev -- --host 127.0.0.1 --port 4173" --port 4173 -- python scripts/verify_results_page.py`
Expected: The browser verification script confirms the hero summary is present, the details section exists, and clicking a timeline phase updates video position.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/PhaseTimeline.tsx frontend/src/components/VideoPlayer.tsx frontend/src/pages/ResultsPage.tsx frontend/src/index.css scripts/verify_results_page.py
git commit -m "feat: add interactive swing timeline and polish results page"
```

## Self-Review Checklist

- Spec coverage:
  - executive-first page structure is covered by Tasks 1 and 2
  - diagnostics demotion is covered by Task 3
  - interactive timeline is covered by Task 4
  - design polish and responsive/accessibility work are covered by Tasks 2 through 4
- Placeholder scan:
  - no `TODO`, `TBD`, or "handle later" placeholders remain in the task steps
- Type consistency:
  - `ExecutiveSummaryModel`, `VideoPlayerHandle`, `DetailsDiagnostics`, and `PhaseTimelineProps` are introduced before later tasks rely on them

## Recommended Commit Sequence

1. `feat: add executive summary hero to results page`
2. `feat: add executive swing takeaways and action plan`
3. `feat: move swing diagnostics into secondary details section`
4. `feat: add interactive swing timeline and polish results page`
