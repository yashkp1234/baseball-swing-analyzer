# Results Interpretive Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `results/demo` into a real report surface, remove the extra clutter from the results page, and replace the misleading 3D story with a cleaner interpretive replay that fits this softball swing.

**Architecture:** Keep the redesign frontend-first. Add a demo results fixture, simplify `ResultsPage` to one primary story surface plus collapsed details, and extend `AnimatedSwingReplay` so it shows estimated bat, contact, ball, and exit trajectory with explicit uncertainty-aware copy.

**Tech Stack:** React 19, TypeScript, Vitest, Vite, existing pose-derived viewer JSON.

---

## File Structure

- Create: `frontend/src/lib/demoResults.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/pages/ResultsPage.test.tsx`
- Modify: `frontend/src/components/AnimatedSwingReplay.tsx`
- Modify: `frontend/src/components/WhatIfSimulator.tsx`
- Modify: `frontend/src/components/ImprovementPlan.tsx` only if tests require import compatibility; otherwise leave unused
- Modify: `frontend/src/components/AnimatedSwingReplay.test.tsx`

## Task 1: Make `results/demo` a real completed report

**Files:**
- Create: `frontend/src/lib/demoResults.ts`
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Test: `frontend/src/pages/ResultsPage.test.tsx`

- [ ] **Step 1: Write the failing test**

Add this test to `frontend/src/pages/ResultsPage.test.tsx`:

```tsx
test("renders a real demo results page without the processing state", () => {
  mockUseQuery.mockImplementation(({ queryKey }) => {
    if (queryKey?.[0] === "status") return { data: undefined } as never;
    if (queryKey?.[0] === "results") return { data: undefined } as never;
    return { data: undefined } as never;
  });

  const html = renderToStaticMarkup(
    <MemoryRouter initialEntries={["/results/demo"]}>
      <Routes>
        <Route path="/results/:jobId" element={<ResultsPage />} />
      </Routes>
    </MemoryRouter>,
  );

  expect(html).toContain("Annotated Video");
  expect(html).not.toContain("Queueing your clip");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- ResultsPage
```

Expected: FAIL because `results/demo` currently depends on job status/results queries.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/lib/demoResults.ts` with a demo `JobResults` fixture built from the same metrics shape used in tests.

Update `ResultsPage.tsx` so:

```tsx
const isDemo = jobId === "demo";
```

and the page uses demo status/results values when `isDemo` is true instead of querying the API.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm test -- ResultsPage
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/demoResults.ts frontend/src/pages/ResultsPage.tsx frontend/src/pages/ResultsPage.test.tsx
git commit -m "feat: add first-class demo results payload"
```

## Task 2: Strip the results page down to the core story

**Files:**
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Test: `frontend/src/pages/ResultsPage.test.tsx`

- [ ] **Step 1: Write the failing test**

Add this test:

```tsx
test("keeps the primary results page focused and removes the bulky practice plan section", () => {
  mockUseQuery.mockReturnValueOnce({ data: status } as never).mockReturnValueOnce({ data: results } as never);

  const html = renderToStaticMarkup(
    <MemoryRouter initialEntries={["/results/job-123"]}>
      <Routes>
        <Route path="/results/:jobId" element={<ResultsPage />} />
      </Routes>
    </MemoryRouter>,
  );

  expect(html).toContain("Annotated Video");
  expect(html).toContain("What's working");
  expect(html).toContain("Details and diagnostics");
  expect(html).not.toContain("Your Practice Plan");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- ResultsPage
```

Expected: FAIL because the page still renders `ImprovementPlan`.

- [ ] **Step 3: Write minimal implementation**

Update `ResultsPage.tsx` to:

- remove `ImprovementPlan`
- keep the hero/video section
- add a compact replay section before takeaways
- keep `DetailsDiagnostics` as the only lower section

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm test -- ResultsPage
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ResultsPage.tsx frontend/src/pages/ResultsPage.test.tsx
git commit -m "refactor: simplify results page hierarchy"
```

## Task 3: Redesign the replay as an interpretive swing read

**Files:**
- Modify: `frontend/src/components/AnimatedSwingReplay.tsx`
- Modify: `frontend/src/components/AnimatedSwingReplay.test.tsx`

- [ ] **Step 1: Write the failing test**

Create or update `frontend/src/components/AnimatedSwingReplay.test.tsx` with:

```tsx
test("renders estimated contact and exit-trajectory cues instead of exact tracking claims", () => {
  const html = renderToStaticMarkup(
    <AnimatedSwingReplay
      currentFrame={2}
      contactFrame={1}
      frames={[
        {
          keypoints: [[0, 0, 0], [1, 1, 0]],
          keypoint_names: ["nose", "left_eye"],
          skeleton: [[0, 1]],
          phase: "load",
          efficiency: 0.4,
          velocities: {},
          bat: { handle: [0, 0, 0], barrel: [0.8, 0.2, 0], confidence: 0.8, estimate_basis: "wrist_forearm_proxy" },
        },
        {
          keypoints: [[0.1, 0.1, 0], [1.1, 1, 0]],
          keypoint_names: ["nose", "left_eye"],
          skeleton: [[0, 1]],
          phase: "contact",
          efficiency: 0.5,
          velocities: {},
          bat: { handle: [0.1, 0.1, 0], barrel: [1.0, 0.3, 0], confidence: 0.8, estimate_basis: "wrist_forearm_proxy" },
        },
        {
          keypoints: [[0.2, 0.2, 0], [1.2, 1, 0]],
          keypoint_names: ["nose", "left_eye"],
          skeleton: [[0, 1]],
          phase: "follow_through",
          efficiency: 0.6,
          velocities: {},
          bat: { handle: [0.2, 0.2, 0], barrel: [1.2, 0.5, 0], confidence: 0.8, estimate_basis: "wrist_forearm_proxy" },
        },
      ]}
    />,
  );

  expect(html).toContain("Interpretive replay");
  expect(html).toContain("Estimated contact");
  expect(html).toContain("Estimated exit path");
  expect(html).not.toContain("measured bat-tracking");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- AnimatedSwingReplay
```

Expected: FAIL because the current replay copy and visuals do not include those cues.

- [ ] **Step 3: Write minimal implementation**

Update `AnimatedSwingReplay.tsx` to:

- change the primary badge from `Replay` to `Interpretive replay`
- compute a simple estimated contact point from the contact-frame barrel
- compute a short estimated exit path polyline that extends from contact in the current bat direction with a slight upward lift
- render:
  - contact marker
  - ball marker at contact
  - dashed estimated exit path
- revise lower copy blocks to explicitly call the path and trajectory estimated

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm test -- AnimatedSwingReplay
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AnimatedSwingReplay.tsx frontend/src/components/AnimatedSwingReplay.test.tsx
git commit -m "feat: redesign replay as interpretive swing read"
```

## Task 4: Gate unreliable claims on the results surface

**Files:**
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/components/AnimatedSwingReplay.tsx`
- Test: `frontend/src/pages/ResultsPage.test.tsx`

- [ ] **Step 1: Write the failing test**

Add this test:

```tsx
test("suppresses exact movement claims when the clip warnings mark them unreliable", () => {
  mockUseQuery.mockReturnValueOnce({ data: status } as never).mockReturnValueOnce({
    data: {
      ...results,
      metrics: {
        ...metrics,
        analysis_quality: {
          status: "reportable",
          can_generate_report: true,
          summary: "usable",
          reasons: [],
          warnings: ["The attack-angle estimate is outside the useful pose-only range."],
          reason_codes: ["attack_angle_artifact", "clipped_body_motion_metric"],
          unreliable_metrics: {
            attack_angle_deg: "bad",
            head_displacement_total: "bad",
          },
        },
      },
    },
  } as never);

  const html = renderToStaticMarkup(
    <MemoryRouter initialEntries={["/results/job-123"]}>
      <Routes>
        <Route path="/results/:jobId" element={<ResultsPage />} />
      </Routes>
    </MemoryRouter>,
  );

  expect(html).toContain("timing, shape, path, and finish");
  expect(html).not.toContain("head movement");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- ResultsPage
```

Expected: FAIL because the results page does not yet provide warning-aware replay framing.

- [ ] **Step 3: Write minimal implementation**

Add warning-aware props to `AnimatedSwingReplay`:

```tsx
reliabilityNote?: string;
hideHeadCallout?: boolean;
```

From `ResultsPage.tsx`, derive these from `analysis_quality.unreliable_metrics` and pass a concise note such as:

```tsx
"Use this view for timing, shape, path, and finish. Exact rotation and bat/ball measurements are estimated or unavailable on this clip."
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend
npm test -- ResultsPage AnimatedSwingReplay
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ResultsPage.tsx frontend/src/pages/ResultsPage.test.tsx frontend/src/components/AnimatedSwingReplay.tsx frontend/src/components/AnimatedSwingReplay.test.tsx
git commit -m "fix: gate unreliable replay claims"
```

## Task 5: Verify the redesigned page end to end

**Files:**
- No required code changes unless verification finds issues

- [ ] **Step 1: Run frontend tests**

Run:

```bash
cd frontend
npm test
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 3: Verify in the browser**

Open `http://127.0.0.1:5176/results/demo` and confirm:

- demo page shows a real report, not the processing screen
- improvement-plan clutter is gone
- interpretive replay is visible near the main clip
- replay shows estimated contact and exit path
- details remain collapsed and secondary

- [ ] **Step 4: Commit verification fixes if needed**

```bash
git add <files>
git commit -m "fix: polish interpretive replay results flow"
```
