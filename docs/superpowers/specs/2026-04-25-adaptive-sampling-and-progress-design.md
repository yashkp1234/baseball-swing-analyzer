# Adaptive Sampling and Progress Design

**Goal**

Increase swing analysis quality by processing more useful frames on GPU, keep end-to-end uploads under 20 seconds for normal local use, and expose enough backend telemetry for the frontend to present honest progress and run-quality context.

**Problem**

The current backend uses a simple uniform sampler in `src/baseball_swing_analyzer/analyzer.py` with a GPU budget of `15 fps / 48 frames`. That is much better than the old CPU emergency cap, but it still leaves quality on the table because:

- frames are spent uniformly across the whole clip, including dead time before and after the swing
- job progress is coarse and not tied to actual inference work
- the frontend results and waiting views cannot explain what the backend actually did

The user priority is:

1. keep uploads below 20 seconds
2. make the waiting state clear and trustworthy
3. push quality as high as possible within that budget

## Approaches Considered

### Option A: Raise uniform GPU limits only

Increase GPU sampling from `15/48` to a higher fixed budget like `24/72`.

**Pros**
- simplest implementation
- immediate quality gain

**Cons**
- risks violating the 20 second budget on longer clips
- still wastes frames outside the swing window
- frontend remains opaque

### Option B: Phase-aware bounded sampling with progress telemetry

Run a cheap coarse pass across the clip, detect the likely swing window, then spend a denser frame budget around the action. Add progress reporting and expose sampling metadata to the frontend.

**Pros**
- best quality per second
- fits the latency target better than brute force
- gives the frontend honest progress and quality context

**Cons**
- more moving parts than a simple limit bump

### Option C: Full streaming pipeline rewrite

Rework analysis into a multi-stage streaming pipeline with persistent intermediate artifacts and detailed task orchestration.

**Pros**
- highest long-term flexibility

**Cons**
- too large for this iteration
- delays the frame-quality and progress wins the user wants now

**Recommendation**

Choose **Option B**. It is the best match for the current codebase and the user goal: better quality without regressing perceived responsiveness.

## Success Criteria

These are the release gates for this work.

### Performance

- For local GPU runs on the current machine, a reference swing clip up to `12 seconds` and up to `1080p60` completes from upload request accepted to completed job in **under 20.0 seconds**.
- The backend must record and expose `analysis_duration_ms` so this can be measured directly.
- GPU jobs must process **more sampled frames than the current 48-frame baseline** on the same class of clip unless the runtime budget forces a fallback.

### Quality

- GPU jobs should target at least **72 sampled frames** when the runtime budget allows it.
- Sampling must become **action-weighted**, meaning the swing window receives denser sampling than dead time before and after the swing.
- Results payload must include enough metadata for the frontend to show:
  - source frame count
  - source fps
  - sampled frame count
  - effective analysis fps
  - pose device used

### Progress UX

- Status polling must expose a stable `current_step` and numeric `progress`.
- During pose inference, progress must advance based on actual processed sampled frames, not only broad stage changes.
- The waiting UI must show:
  - a determinate progress bar
  - a human-readable current step
  - sampled frame progress when available

### Safety

- If a GPU job cannot stay within the configured runtime budget, it must reduce sampling density before failing.
- If adaptive sampling cannot identify a swing window confidently, it must fall back to bounded uniform sampling rather than erroring.
- Existing job creation, results fetch, and viewer entry flows must continue to work.

## Scope

### In Scope

- backend sampling strategy
- backend job progress reporting
- results payload metadata
- frontend processing/wait state improvements
- frontend display of analysis metadata relevant to density and quality
- benchmark and validation for latency target

### Out of Scope

- redesigning the 3D viewer visuals
- replacing the pose model
- changing coaching generation logic
- large database or queue architecture changes

## Design

### 1. Adaptive bounded sampling

The analyzer will move from a single uniform sampler to a bounded two-stage sampler.

#### Stage 1: coarse scan

- Sample the full clip sparsely to estimate motion intensity over time.
- Use existing pose-friendly signals already available from coarse keypoints, such as wrist velocity, hip rotation change, shoulder rotation change, and overall upper-body motion.
- Detect a candidate swing window spanning load, stride, contact, and early follow-through.

#### Stage 2: dense action sampling

- Allocate most of the sampling budget inside the candidate window.
- Keep a smaller coarse sample outside that window to preserve context and phase continuity.
- If the clip is short enough, use the full higher-quality GPU budget without needing aggressive downsampling.

#### Runtime budgeting

- Add a configurable GPU runtime budget, for example `SWING_ANALYSIS_TARGET_RUNTIME_MS_GPU`.
- Start from a preferred density target such as `24 fps / 72 frames`.
- If estimated work exceeds budget, reduce density in controlled steps.
- Never exceed a hard upper bound on sampled frames.

### 2. Analyzer telemetry

The analyzer should return structured metadata alongside metrics so downstream layers can explain what happened.

Planned metadata fields:

- `pose_device`
- `source_frames`
- `source_fps`
- `sampled_frames`
- `sampled_indices`
- `effective_analysis_fps`
- `sampling_mode` (`uniform` or `adaptive`)
- `analysis_duration_ms`
- `pose_inference_duration_ms`
- `progress_frame_total`

`sampled_indices` may stay backend-only if payload size becomes annoying; the frontend does not need it immediately.

### 3. Job progress model

`server/tasks/analyze.py` currently updates progress in broad jumps. That should become a staged model with real sub-progress:

- `queued`
- `loading_video`
- `sampling`
- `pose_inference`
- `computing_metrics`
- `generating_coaching`
- `generating_3d_data`
- `finalizing`
- `done`

During `pose_inference`, update progress using processed sampled frames:

- `progress_detail_current`
- `progress_detail_total`
- optional short `progress_detail_label` like `frames`

This lets the frontend show `18 / 72 frames analyzed` instead of a fake spinner.

### 4. Results and status API changes

#### Status response

Extend job status responses to include optional detail fields:

- `current_step`
- `progress`
- `progress_detail_current`
- `progress_detail_total`
- `progress_detail_label`

#### Results response

Extend the completed results payload with an `analysis` object:

- `pose_device`
- `source_frames`
- `source_fps`
- `sampled_frames`
- `effective_analysis_fps`
- `sampling_mode`
- `analysis_duration_ms`

This keeps metrics separate from run metadata and gives the frontend a stable contract.

### 5. Frontend UX

#### Processing state

Update the processing view to show:

- determinate progress bar
- current stage label
- frame progress when present
- short copy that sets expectations without fluff

#### Results and viewer context

Show a compact analysis summary near the timeline or viewer entry:

- `GPU` or `CPU`
- sampled frames
- effective fps
- analysis runtime

This helps the user understand whether a result is dense and high-confidence or a lower-budget fallback.

## Milestones

These are the commit and push checkpoints for implementation.

### M1: Progress telemetry foundation

**Output**
- database schema extended for detail progress fields
- analysis task emits structured stage progress
- status API returns richer progress data

**Success check**
- a live job shows determinate stage progress in polling responses

**Commit**
- `feat: add detailed analysis progress telemetry`

### M2: Adaptive GPU sampling

**Output**
- bounded adaptive sampler in `analyzer.py`
- higher preferred GPU density target
- safe fallback to bounded uniform sampling
- analyzer returns analysis metadata

**Success check**
- reference GPU jobs process more than 48 sampled frames while staying under target runtime

**Commit**
- `feat: add adaptive bounded swing sampling`

### M3: Frontend wait-state improvements

**Output**
- `ProcessingStatus` shows real progress bar and detail counts
- frontend uses richer status payload without regressions

**Success check**
- waiting view shows stage + determinate progress + frame counts during live processing

**Commit**
- `feat: improve job progress UI`

### M4: Results metadata handoff

**Output**
- results payload exposes analysis metadata
- results page and viewer surface key run metadata cleanly

**Success check**
- results page shows device, sampled frames, effective fps, and runtime for completed jobs

**Commit**
- `feat: surface analysis quality metadata`

### M5: Benchmarks and tuning

**Output**
- reference benchmark script or fixture-driven verification
- tuned GPU defaults that pass the latency target

**Success check**
- reference clip completes under 20 seconds end-to-end on the current machine

**Commit**
- `perf: tune adaptive sampling for latency target`

## Testing Strategy

### Backend

- unit tests for adaptive sampling behavior:
  - short clip uses dense budget directly
  - long clip concentrates frames in action window
  - low-confidence action window falls back to uniform bounded sampling
- unit tests for progress field updates
- regression tests for results/status payload shape

### Frontend

- component tests for processing progress rendering
- integration test for status polling transition from queued to completed
- rendering test for results metadata block

### End-to-end

- run one real local job and verify:
  - progress steps advance sensibly
  - frame counts appear while processing
  - completed results include analysis metadata
  - total runtime stays under 20 seconds for the reference clip

## Risks and Mitigations

### Risk: adaptive sampling picks the wrong window

**Mitigation**
- preserve uniform fallback
- keep pre/post-window context samples

### Risk: frontend becomes tightly coupled to transient backend details

**Mitigation**
- keep analysis metadata in a dedicated `analysis` object
- keep detail fields optional in status responses

### Risk: extra telemetry bloats stored payloads

**Mitigation**
- keep detailed arrays like sampled indices out of the public payload unless needed
- store only summary metadata in the job row

## Implementation Notes

- Avoid touching unrelated viewer redesign work.
- Keep milestone diffs narrow enough to review and revert independently.
- Prefer additive API evolution so existing frontend calls do not break mid-implementation.
