# Executive Swing Summary Redesign

Date: 2026-04-25
Status: Proposed
Scope: `frontend/src/pages/ResultsPage.tsx` and supporting result-page components

## Goal

Redesign the swing analysis results page so it reads like an executive summary for a player or coach rather than a diagnostics dashboard. The page should answer, in order:

1. What happened in this swing?
2. What was good?
3. What was hurting performance?
4. What should the player improve next?
5. Where is the visual proof that these takeaways match the actual swing?

Operational details such as device, sampling mode, runtime, and analysis throughput should remain available, but they should no longer compete with the main story of the swing.

## User Intent

The primary user wants a page that feels polished, modern, and intentional. Every visible element should serve a coaching purpose. Anything that is not directly useful to the player or coach should either move into a lower-priority details section or become logging/diagnostic information outside the main summary flow.

The annotated video remains essential because it proves the system analyzed the real swing and gives the user confidence that the written takeaways match what happened on screen.

## Design Direction

Use a dark, premium training-tool aesthetic with stronger visual hierarchy, consistent iconography, and calmer typography. The page should feel more like a high-end performance report than a developer console.

Design principles:

- Put the swing story ahead of processing metadata.
- Make the page scannable in under 10 seconds.
- Keep the annotated video near the top and visually prominent.
- Use icons when they clarify meaning, not as decoration.
- Prefer grouped sections with clear purpose over many equal-weight cards.
- Reserve dense raw metrics and timing metadata for a details area.

## Information Architecture

The redesigned page will have six content layers.

### 1. Hero Summary

This is the executive summary band at the top of the page.

Contents:

- Overall swing score
- Short swing label or quality descriptor
- One-sentence summary of the swing
- Small supporting chips for confidence or profile tags only if they help interpretation

Purpose:

- Give the user an immediate answer before any deep reading.
- Establish the tone and value of the analysis.

This section replaces the current "Analysis Summary" panel as the topmost focal point.

### 2. Annotated Video Evidence

The annotated video should sit high on the page, directly under or beside the hero summary depending on viewport width.

Contents:

- Annotated video player
- Short caption explaining that this is the evidence layer for the summary
- Optional quick-jump controls only if they connect to meaningful swing moments

Purpose:

- Prove the analysis matches the real swing.
- Give coaches and players a shared reference point while reading strengths and issues.

### 3. What Is Working

This section surfaces strengths in plain language.

Contents:

- Two to four prioritized positive takeaways
- Each item should include a concise title, a short explanation, and optionally a supporting metric if it adds clarity

Purpose:

- Reinforce what should be kept.
- Make the report feel balanced and actionable rather than purely critical.

### 4. What Is Costing Performance

This section surfaces the most important problems.

Contents:

- Two to four prioritized issues
- Each item should explain what the issue is and why it matters
- Severity or impact indicators can be used if visually subtle

Purpose:

- Help the user understand what is actually hurting the swing.
- Prevent the metric list from forcing the user to interpret raw numbers alone.

### 5. What To Improve Next

This is the action section.

Contents:

- Short, ordered coaching actions
- Language should be direct, specific, and practice-oriented
- The first action should be clearly presented as the highest-leverage next step

Purpose:

- Convert diagnosis into an immediate training plan.
- Keep the report useful beyond passive review.

The current coaching report content can seed this section, but it should be edited into a tighter, more structured format.

### 6. Details And Diagnostics

This is where lower-priority information moves.

Contents:

- Interactive phase timeline
- Raw metric list
- Processing and analysis metadata:
  - sampling mode
  - device
  - sampled frames
  - effective FPS
  - runtime
  - source frames and source FPS
  - pose inference duration
  - pose confidence

Purpose:

- Preserve transparency and advanced inspection.
- Keep the executive page clean while still supporting power users.

This area can be a collapsible section or a visually lower-priority band near the bottom of the page.

## Timeline Redesign

The timeline should no longer appear as a static strip in the primary reading flow. It should move into the details area and become meaningfully interactive.

Required behavior:

- Hovering a phase reveals a tooltip with:
  - phase name
  - frame range
  - short explanation of what that phase means
- Clicking a phase seeks the video or sets a selected frame anchor if the current page supports it
- The selected phase should be visually distinct
- Important swing events such as stride plant and contact should be marked, labeled, and readable

Purpose:

- Turn the timeline from decorative context into an explorable teaching aid.

## Content Hierarchy Rules

The following rules define what belongs in the main page versus details.

Keep in main summary flow:

- overall score
- short narrative summary
- strengths
- problems
- next actions
- annotated video

Move to details:

- runtime and throughput information
- device and sampling mode
- dense raw metric cards
- frame counts and analysis internals
- timeline unless it is directly tied to a primary explainer interaction

If a piece of information does not help a coach or player interpret the swing or decide what to do next, it should not occupy primary real estate.

## Component-Level Changes

### `ResultsPage`

Restructure the page around purposeful sections instead of evenly weighted cards. The new layout should feel editorial and guided rather than grid-first.

Likely responsibilities:

- assemble hero summary data
- place annotated video high in the layout
- group positives, negatives, and improvement actions into distinct sections
- push operational metadata and timeline into a details section

### `AnalysisSummary`

Repurpose or replace this component.

New responsibility:

- render executive summary information rather than processing metadata

Processing metadata should move into a separate diagnostics component, likely shared with the details area.

### `PhaseTimeline`

Upgrade this component so it supports:

- hoverable, readable explanations
- selected states
- click interaction tied to video/frame navigation
- event markers

### `MetricCard`

Reduce its visual dominance on the main page. Metric cards can remain in the details area or be selectively embedded as evidence inside takeaway sections when they support interpretation.

### `CoachingReport` and `FlagsPanel`

These should be reworked or re-composed into the new sections:

- what is working
- what is costing performance
- what to improve next

They should read as a single coherent report, not as independent widgets.

## Visual System

The redesign should establish a consistent visual system across typography, spacing, icons, and surfaces.

Requirements:

- consistent heading scale and casing
- icon usage for sections and key indicators
- fewer repeated bordered boxes with equal visual weight
- stronger spacing rhythm between major sections
- clear emphasis on the single most important takeaway
- polished hover and focus states

Preferred tone:

- cool
- premium
- athletic
- technical but not clinical

Avoid:

- neon debug-panel styling
- mono-heavy presentation for user-facing narrative content
- every panel looking equally important

## Responsive Behavior

Desktop:

- hero summary and video can share the upper fold if the layout remains balanced
- strengths, issues, and next steps should stack in a readable order without becoming a dashboard wall

Mobile:

- hero summary first
- video immediately after
- strengths, issues, and next steps in a single-column reading flow
- details collapsed or clearly secondary

The page must remain easy to scan without horizontal compression of important text.

## Accessibility And Interaction

- Tooltips and hover states must have keyboard equivalents
- Clickable timeline segments must have visible focus states
- Section contrast should remain legible in the dark theme
- Icons should not be the only carrier of meaning
- Motion should be subtle and supportive

## Data And Mapping Requirements

The redesign may require lightweight presentation helpers that derive:

- an overall score or summary classification from available metrics and flags
- positive takeaways from favorable metrics or flags
- negative takeaways from poor metrics or flags
- prioritized improvement actions from existing coaching lines

These helpers should be presentation-layer transforms, not backend analysis changes, unless frontend data proves insufficient.

## Testing Strategy

Verification should cover:

- desktop and mobile layout sanity
- keyboard access for timeline interaction
- tooltip and selection behavior for phases
- visibility and readability of hero summary and details section
- that analysis metadata still exists, but only in the details area

Use browser-based verification after implementation to confirm that:

- the page feels coherent
- the timeline is actually interactive
- the video remains prominent
- the executive summary is readable without scanning the full page

## Out Of Scope

- changing the core backend metric calculations
- redefining biomechanical metrics
- adding new heavy charting or visualization dependencies
- redesigning the upload flow or 3D viewer in this task

## Recommended Implementation Order

1. Refactor page information architecture in `ResultsPage`
2. Replace metadata-first summary with executive summary component
3. Build a details/diagnostics section for metadata and raw metrics
4. Redesign timeline interaction and connect it to meaningful selection behavior
5. Refactor flags/coaching content into strengths, issues, and next actions
6. Polish spacing, icons, typography, and responsive behavior

## Committable Milestones

### Milestone 1: Executive Summary Skeleton

Scope:

- replace the metadata-first top section with an executive summary hero
- move the annotated video into the upper portion of the page
- remove processing metadata from the top flow

Success criteria:

- the first viewport communicates score, summary, and video evidence
- device/runtime/sampling information no longer appears above the fold
- the page still builds cleanly and existing result fetching behavior remains intact

### Milestone 2: Coaching Narrative Sections

Scope:

- introduce "what is working", "what is costing performance", and "what to improve next"
- repurpose current flags and coaching content into these sections
- reduce the prominence of the raw metric wall

Success criteria:

- the user can identify strengths, issues, and next actions without interpreting raw metrics
- every visible section in the main flow has a clear coaching purpose
- the page remains readable on both desktop and mobile layouts

### Milestone 3: Details And Diagnostics

Scope:

- add a lower-priority details area for metadata, raw metrics, and advanced inspection
- move analysis summary internals into that section
- preserve access to processing transparency without cluttering the executive summary

Success criteria:

- all current metadata remains accessible
- the main page no longer feels like a diagnostics dashboard
- raw metrics and timeline are visually secondary to the executive summary

### Milestone 4: Interactive Timeline Polish

Scope:

- redesign the timeline to support hover, focus, click, and event markers
- connect timeline interaction to meaningful frame or video navigation where possible
- finalize typography, icons, spacing, and motion polish

Success criteria:

- the timeline provides useful explanation on hover and focus
- clicking a phase gives the user meaningful control or context
- the page looks cohesive, polished, and intentionally designed rather than assembled from widgets
