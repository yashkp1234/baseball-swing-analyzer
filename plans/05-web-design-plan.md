# SwingScan — Web App Design & Implementation Plan

## Recommended opencode Skills

Install these from `github.com/anthropics/skills` into `.opencode/skills/`:

| Skill | Why |
|-------|-----|
| **frontend-design** | Core skill — anti-AI-slop design philosophy, typography, color, motion, spatial composition guidelines. Use for every UI build. |
| **web-artifacts-builder** | Full React + Tailwind + shadcn/ui stack with init/bundle scripts. Perfect for building the dashboard UI as a structured project. |
| **webapp-testing** | Playwright-based testing for local web apps. Use to verify upload flow, metric rendering, 3D canvas behavior. |

**Skipped:**
- **canvas-design** — poster/art generation, not web UI
- **theme-factory** — slide theming, not relevant to web app

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    SwingScan Web App                     │
├──────────────┬──────────────────┬────────────────────────┤
│   Frontend   │   FastAPI Backend│   Worker (Celery/ARQ)  │
│   React+TS   │   Python 3.10+  │   Python 3.10+        │
│   Three.js   │   /api/*         │   Runs analysis pipeline│
│   Tailwind   │   WebSocket /ws  │   Stores results in DB │
│   shadcn/ui  │                  │   Publishes 3D data    │
└──────────────┴──────────────────┴────────────────────────┘
        │              │                      │
        └──────────────┼──────────────────────┘
                       │
              ┌────────┴────────┐
              │  SQLite / Redis  │
              │  (job queue +    │
              │   result store)  │
              └─────────────────┘
```

---

## Phase 1: Upload & Metrics Dashboard

### 1.1 Backend API

**File: `src/baseball_swing_analyzer/web/`**

```
web/
├── __init__.py
├── main.py              # FastAPI app entry
├── routes/
│   ├── __init__.py
│   ├── upload.py         # POST /api/swings — accept video, enqueue job
│   ├── results.py        # GET  /api/swings/{id} — return metrics.json + coaching
│   └── ws.py             # WS   /ws/swings/{id} — progress updates
├── models.py             # Pydantic models for API I/O
├── worker.py             # ARQ worker: calls analyze_swing(), stores JSON
└── db.py                 # SQLite via aiosqlite — jobs table
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/swings` | Upload video → returns `{swing_id, status: "queued"}` |
| `GET` | `/api/swings/{id}` | Returns full metrics + flags + coaching |
| `GET` | `/api/swings/{id}/3d` | Returns 3D visualization data (Phase 2) |
| `WS` | `/ws/swings/{id}` | Real-time progress: ` queued → processing → done` |

**Worker flow** (reuses existing pipeline exactly):

```python
# worker.py — thin wrapper around existing code
async def analyze_swing_job(ctx, swing_id: str, video_path: str):
    result = analyze_swing(Path(video_path), output_dir=..., handedness="auto")
    flags = generate_qualitative_flags(result["keypoints_seq_placeholder"], result["phase_labels"])
    result["flags"] = flags
    # store result JSON in DB
    await store_result(swing_id, result)
```

We do NOT change any analysis code. The backend wraps `analyze_swing()` and `generate_qualitative_flags()` as-is.

### 1.2 Frontend — Upload Page

**Stack: React 18 + TypeScript + Vite + Tailwind CSS 3.4 + shadcn/ui**

```
frontend/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/
│   │   ├── UploadZone.tsx        # Drag-and-drop video uploader
│   │   ├── ProcessingStatus.tsx  # WebSocket progress bar
│   │   └── Layout.tsx             # App shell with nav
│   ├── pages/
│   │   ├── UploadPage.tsx
│   │   └── ResultsPage.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   └── useSwingAnalysis.ts
│   ├── lib/
│   │   └── api.ts                 # Axios/fetch wrapper
│   └── index.css
├── package.json
└── vite.config.ts
```

**Design language** (guided by `frontend-design` skill):

- **Typography**: `Instrument Sans` for headings (distinctive, geometric), `IBM Plex Sans` for body (clean, readable)
- **Color**: Dark mode primary. Deep charcoal `#0A0A0A` bg, electric green accent `#00FF87` for positive/bat-speed, warm amber `#FF8A00` for warnings, slate borders `#1E1E1E`
- **Motion**: Staggered fade-in on metric cards. Phase timeline animates width on load. Subtle parallax on hero section.
- **Layout**: Asymmetric — large hero upload zone left, recent analyses sidebar right. Grid-breaking stat cards that overlap slightly on hover.

### 1.3 Frontend — Results Dashboard

The results page renders the **exact same data** as the current CLI output, transformed into an interactive dashboard:

**Sections:**

```
┌──────────────────────────────────────────────────────────────┐
│  SWING ANALYSIS RESULTS                              [New]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │  Phase Timeline  │  │  Swing Skeleton Overlay          │   │
│  │                 │  │  (annotated video or key frames) │   │
│  │  idle→load→    │  │                                  │   │
│  │  stride→swing→│  │  Show skeleton + bbox + phase    │   │
│  │  contact→FT    │  │  label on each frame             │   │
│  │                 │  │                                  │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
│                                                              │
│  ┌─── Key Metrics ──────────────────────────────────────┐   │
│  │                                                      │   │
│  │  Hip Angle      X-Factor      Spine Tilt           │   │
│  │  170.3°         31.3°         10.7°                 │   │
│  │                                                      │   │
│  │  L Knee          R Knee        Head Disp           │   │
│  │  1.5°            41.0°        42.0 px              │   │
│  │                                                      │   │
│  │  Peak Wrist Vel  Contact Frame   Stride Plant      │   │
│  │  1,969 px/s      Frame 166        Frame 40          │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─── Qualitative Flags ───────────────────────────────┐   │
│  │  Handedness: Right  |  Leg Action: Neither          │   │
│  │  Shoulder: Closed   |  Finish: Low  |  Slot: Low    │   │
│  │  Hip Casting: No                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─── Coaching Report ─────────────────────────────────┐   │
│  │  [Biomechanical Cues]                                │   │
│  │  • X-factor of 31° is in a good range...            │   │
│  │  • Low finish suggests...                            │   │
│  │  [AI-Generated Insights]                            │   │
│  │  • ...                                               │   │
│  │  [3D Visualization →]   ← links to Phase 2         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─── Phase Durations ─────────────────────────────────┐   │
│  │  idle: 302fr | load: 4fr | stride: 0fr | swing: 9 │   │
│  │  contact: 1fr | follow_through: 17fr               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Phase Timeline** — horizontal bar, color-coded per phase:
- `idle` → muted gray
- `load` → teal
- `stride` → blue
- `swing` → electric green `#00FF87`
- `contact` → hot highlight `#FFD700`
- `follow_through` → amber fade

Each metric card uses a subtle radial gradient background matching the metric's "zone" (green = good, amber = moderate, red = needs work). Zone thresholds derived from the existing `knowledge.py` RULES.

**Data mapping from current output:**

```typescript
// Current metrics.json → Dashboard mapping
interface SwingMetrics {
  phase_durations: Record<string, number>;    // → Phase Timeline bar widths
  stride_plant_frame: number;                  // → Key Metric card
  contact_frame: number;                       // → Key Metric card
  hip_angle_at_contact: number;                // → Key Metric card
  shoulder_angle_at_contact: number;           // → Key Metric card
  x_factor_at_contact: number;                 // → Key Metric card, highlighted
  spine_tilt_at_contact: number;               // → Key Metric card
  left_knee_at_contact: number;                // → Key Metric card
  right_knee_at_contact: number;               // → Key Metric card
  head_displacement_total: number;             // → Key Metric card
  wrist_peak_velocity_px_s: number;           // → Key Metric card, prominent
  frames: number;                              // → Phase Timeline total
  fps: number;                                 // → Timestamps
  phase_labels: string[];                      // → Phase Timeline colors
  flags: {                                     // → Qualitative Flags panel
    handedness: string;
    front_shoulder_closed_load: boolean;
    leg_action: string;
    finish_height: string;
    hip_casting: boolean;
    arm_slot_at_contact: string;
  };
}
```

The coaching report (`coaching.md`) is parsed and rendered as three collapsible sections matching the current output structure (Biomechanical Cues / AI Insights / Vision Analysis).

---

## Phase 2: 3D Visualization

### 2.1 Design Goals

Create a cinematic 3D replay of the batter's swing that:
1. **Reconstructs the batter as an articulated figure** from the 17 COCO keypoints
2. **Animates the full swing** frame-by-frame using the keypoint time series
3. **Shows velocity vectors** on wrists, elbows, hips — color-coded by magnitude
4. **Highlights energy transfer zones** — where velocity transfers through the kinetic chain (hips → shoulders → hands → bat)
5. **Marks the "velocity loss" moments** — where kinetic energy dissipates (early hip opening, casting, deceleration)
6. **Provides scrubber/playback controls** synced to phase labels

### 2.2 3D Data Pipeline

We need to lift 2D keypoints into 3D. Options:

| Approach | Quality | Complexity |
|----------|---------|-----------|
| **A. Simple triangulation** | Low — assumes a plane | Minimal |
| **B. Use pretrained 3D lifter** (e.g., VideoPose3D, MotionBERT) | Medium-High | Medium |
| **C. Use MediaPipe 3D or TRT pose** | High | Medium |

**Recommended: Approach B** — Use a lightweight 3D pose lifter model to convert `(T, 17, 2)` → `(T, 17, 3)` coordinate arrays. This is the minimum viable change to the existing pipeline.

**New module: `src/baseball_swing_analyzer/lifter.py`**

```python
def lift_to_3d(keypoints_2d: NDArray, fps: float) -> NDArray:
    """Lift (T, 17, 2+) keypoint sequence to (T, 17, 3) 3D coordinates.

    Uses a pretrained model (MotionBERT or VideoPose3D) to infer depth.
    Falls back to heuristic triangulation if model unavailable.
    """
```

**New 3D visualization data output** added to metrics.json:

```json
{
  "keypoints_3d": [           // (T, 17, 3) — 3D joint positions
    [[x, y, z], ...17 joints],
    ...
  ],
  "velocity_vectors": {       // Per-joint velocity in 3D
    "left_wrist":  [[vx, vy, vz], ...T frames],
    "right_wrist": [[vx, vy, vz], ...T frames],
    "left_hip":    [...],
    "right_hip":   [...],
    "left_shoulder":[...],
    "right_shoulder":[...]
  },
  "energy_loss_events": [     // Moments where velocity drops
    {
      "frame": 162,
      "joint": "right_wrist",
      "type": "deceleration",
      "magnitude_pct": 15.2,
      "description": "Bat deceleration before contact — early hip opening"
    }
  ],
  "kinetic_chain_scores": {   // Efficiency of energy transfer
    "hip_to_shoulder": 0.87,  // correlation of velocity transfer
    "shoulder_to_hand": 0.72,
    "overall_efficiency": 0.79
  }
}
```

### 2.3 Computing Velocity Loss & Energy Transfer

**New module: `src/baseball_swing_analyzer/energy.py`**

This computes where velocity is gained and lost in the kinetic chain:

```python
def compute_kinetic_chain(
    keypoints_3d: NDArray,    # (T, 17, 3)
    fps: float
) -> dict:
    """Compute velocity vectors and kinetic chain efficiency.

    For each frame:
    1. Compute 3D velocity of each joint (finite differences)
    2. Compute acceleration (velocity derivative)
    3. Identify deceleration events (velocity drops > threshold)
    4. Compute cross-correlation between sequential joints to measure
       energy transfer efficiency (hip→shoulder→hand→bat)

    Returns velocity_vectors, energy_loss_events, kinetic_chain_scores.
    """
```

**Energy loss detection logic:**

1. Compute per-joint 3D velocity: `v[t] = (pos[t+1] - pos[t-1]) / (2*dt)`
2. Compute per-joint acceleration: `a[t] = (v[t+1] - v[t-1]) / (2*dt)`
3. Detect negative acceleration spikes (deceleration > 2σ from mean)
4. Cross-correlate sequential joint velocities in the kinetic chain:
   - Hip velocity leads shoulder velocity by ~2-4 frames (good = tight coupling)
   - Shoulder velocity leads hand velocity by ~1-3 frames
   - Low correlation = energy leak (e.g., hip casts out, hands drag)

**Mapping to coaching terms:**

| Event | Detection | Meaning |
|-------|-----------|---------|
| Early hip opening | Hip velocity rises while shoulder velocity flat/declining before swing | "Hip casting" |
| Bat drag | Hand velocity lags shoulder velocity by >4 frames | Late hands |
| Deceleration before contact | Peak wrist velocity occurs >3 frames before contact frame | Suboptimal timing |
| Push-off loss | Front knee velocity drops suddenly during stride | Poor weight transfer |

### 2.4 3D Frontend — Three.js Visualization

**File: `frontend/src/components/ThreeVisualization.tsx`**

```
components/
├── ThreeVisualization.tsx      # Main canvas component
├── BatterFigure.tsx            # Articulated 3D skeleton figure
├── VelocityArrows.tsx          # 3D arrow overlays for velocity vectors
├── EnergyLossMarkers.tsx       # Glowing markers on joints where energy leaks
├── KineticChainRings.tsx        # Concentric rings showing chain efficiency
├── PlaybackControls.tsx        # Play/pause, scrubber, speed, phase labels
└── PhaseTimeline3D.tsx         # Side panel: phase scrubber synced to 3D
```

**Visual Design:**

- **Batter figure**: Articulated stick figure using cylindrical limbs + sphere joints. Dark body (`#333`) with highlighted joint spheres.
- **Velocity arrows**: Green (`#00FF87`) arrows at wrists showing bat speed direction & magnitude. Arrow length = velocity magnitude. Color transitions:
  - Green `#00FF87` = accelerating
  - Yellow `#FFD700` = peak
  - Red `#FF4444` = decelerating / velocity loss
- **Energy loss events**: Pulsing red circles at the joint where energy leaks. Size = severity. Text label fades in: "Hip casting — 15% energy loss"
- **Kinetic chain rings**: Semi-transparent concentric rings around the torso. Inner = hips, middle = shoulders, outer = bat. Ring opacity pulses with the velocity of that segment. When energy transfers poorly, a ring dims/flickers.
- **Background**: Dark gradient `#0A0A0A → #111`. Subtle grid floor. Camera orbits slowly when idle, follows the batter during playback.
- **Playback**: Timeline scrubber at bottom with phase labels (color-coded same as dashboard). Play/pause. Speed toggle (0.25x, 0.5x, 1x, 2x). Phase jump buttons.

**Animation flow:**

1. Video uploaded → metrics computed → 3D data generated
2. User clicks "3D Visualization" on results page
3. Three.js scene loads with the batter in stance (frame 0)
4. Auto-plays through the swing with velocity arrows and loss markers
5. User can scrub, pause, jump to phases
6. Key moments highlighted with a brief slow-motion effect:
   - Stride foot plant
   - Contact frame
   - Peak wrist velocity point

### 2.5 Phase 2 Backend Additions

```python
# web/routes/results.py — new endpoint
@router.get("/api/swings/{swing_id}/3d")
async def get_3d_data(swing_id: str):
    result = await get_result(swing_id)
    kps_2d = np.array(result["keypoints_seq"])  # stored from analysis
    kps_3d = lift_to_3d(kps_2d, result["fps"])
    energy = compute_kinetic_chain(kps_3d, result["fps"])
    return {
        "keypoints_3d": kps_3d.tolist(),
        "velocity_vectors": energy["velocity_vectors"],
        "energy_loss_events": energy["energy_loss_events"],
        "kinetic_chain_scores": energy["kinetic_chain_scores"],
        "phase_labels": result["phase_labels"],
        "fps": result["fps"],
        "contact_frame": result["contact_frame"],
        "stride_plant_frame": result["stride_plant_frame"],
    }
```

---

## Implementation Order

### Sprint 1 — Backend API + Upload
1. Create `src/baseball_swing_analyzer/web/` package
2. FastAPI app with upload endpoint, job queue (ARQ + Redis)
3. Worker that calls existing `analyze_swing()` pipeline
4. WebSocket progress updates
5. SQLite job storage
6. **Tests**: POST video → get job ID → poll until done → get metrics

### Sprint 2 — Frontend Upload + Results Dashboard
1. `npx create vite frontend --template react-ts`
2. Install Tailwind, shadcn/ui
3. Build upload page (drag-drop, progress bar via WS)
4. Build results page rendering all metrics.json fields
5. Phase timeline visualization
6. Coaching report renderer (markdown → styled sections)
7. **Test with Playwright** (use `webapp-testing` skill)

### Sprint 3 — 3D Pose Lifter + Energy Analysis
1. Add `lifter.py` module — integrate MotionBERT or similar
2. Add `energy.py` module — velocity vectors, loss detection, chain scores
3. Wire into pipeline (opt-in flag `--3d` on CLI, always-on via API)
4. Store 3D data alongside metrics.json
5. **Tests**: Verify lift_to_3d output shape, energy loss detection accuracy

### Sprint 4 — 3D Visualization Frontend
1. Install Three.js + React Three Fiber
2. Build `ThreeVisualization.tsx` with articulated figure
3. Add velocity arrows with color-coded magnitude
4. Add energy loss markers (pulsing red circles)
5. Add kinetic chain rings
6. Build playback controls + phase scrubber
7. Wire to `/api/swings/{id}/3d` endpoint
8. **Test with Playwright**

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend framework | FastAPI | Python-native, async, matches existing codebase language |
| Job queue | ARQ (asyncio + Redis) | Lightweight, no Celery overhead, Python-native |
| Frontend framework | React + TypeScript + Vite | Matches `web-artifacts-builder` skill stack, shadcn/ui ecosystem |
| UI components | shadcn/ui | Copy-paste, customizable, great DX |
| 3D library | React Three Fiber | Declarative Three.js in React, excellent animation support |
| 3D pose lifting | MotionBERT / VideoPose3D | Best quality open-source lifters for monocular video |
| Database | SQLite (aiosqlite) | Simple, no infra, adequate for single-user / small team |
| Design skill | frontend-design | Anti-AI-slop philosophy, bold typography, intentional color |
| Testing skill | webapp-testing | Playwright automation for end-to-end verification |

---

## Mockup — Results Dashboard (Wireframe)

```
╭──────────────────────────────────────────────────────────────╮
│  ⚾ SwingScan                              [New Analysis]    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─── Phase Timeline ─────────────────────────────────────┐  │
│  │  idle▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ load░ stride░ swing▓▓ contact▓ │  │
│  │  follow_through▓▓▓▓                                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── Swing Replay ────────┐  ┌── Key Metrics ──────────┐  │
│  │                          │  │                          │  │
│  │   [Annotated video or    │  │  ┌─────┐ ┌─────┐       │  │
│  │    key frames with       │  │  │ 31° │ │170°│       │  │
│  │    skeleton overlay]     │  │  │X-Fac│ │Hip  │       │  │
│  │                          │  │  └─────┘ └─────┘       │  │
│  │   ▶ ‖■■■■■■■■□□□□ 0:05  │  │  ┌─────┐ ┌─────┐       │  │
│  │                          │  │  │1969 │ │ 42  │       │  │
│  └──────────────────────────┘  │  │WrlVel│ │Head │       │  │
│                                │  └─────┘ └─────┘       │  │
│                                │  ┌─────┐ ┌─────┐       │  │
│                                │  │11°  │ │ 41° │       │  │
│                                │  │Spine│ │RKnee│       │  │
│                                │  └─────┘ └─────┘       │  │
│                                └──────────────────────────┘  │
│                                                              │
│  ┌─── Flags ─────────────────────────────────────────────┐  │
│  │  🏏 Right-handed  ✓ Shoulder closed  ⚠ Low finish    │  │
│  │  ✗ No leg kick  ⚠ Low arm slot  ✓ No hip casting   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── Coaching ──────────────────────────────────────────┐  │
│  │  ► Biomechanical Cues (3)                              │  │
│  │  ► AI Coaching Insights (4)                           │  │
│  │  ► Vision Analysis                                    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── 3D Visualization ──────────────────────────────────┐  │
│  │                                                        │  │
│  │   [🔬 Launch 3D Swing Replay]                         │  │
│  │   See velocity vectors, energy transfer, and           │  │
│  │   velocity loss points animated on a 3D batter.       │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

---

## Mockup — 3D Visualization Screen

```
╭──────────────────────────────────────────────────────────────╮
│  ← Back to Results                   Swing: contact (4/6)  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│              ┌─────────────────────────────────┐             │
│              │                                 │             │
│              │    ╱●╲        ← head            │             │
│              │   │ ● │                          │             │
│              │   └─┬─┘                          │             │
│              │     │          ← torso            │             │
│              │    ╱●╲                            │             │
│              │   │ ● │  ←←←← ← velocity arrow  │             │
│              │   └─┬─┘     (green = accelerating)│             │
│              │     │                            │             │
│              │    ╱ ╲       ● ← red pulse       │             │
│              │   ●   ●      "15% energy loss"   │             │
│              │  ↙     ↘     at right hip         │             │
│              │ legs w/ velocity                  │             │
│              │                                 │             │
│              │  ⭕ ⭕ ⭕ ← kinetic chain rings    │             │
│              │  (glow = good transfer)          │             │
│              │                                 │             │
│              └─────────────────────────────────┘             │
│                                                              │
│  ┌─ Kinetic Chain Efficiency ─────────────────────────────┐  │
│  │  Hip → Shoulder  ██████████░░  87%                     │  │
│  │  Shoulder → Hand  ███████░░░░░  72%  ⚠ below avg      │  │
│  │  Overall          █████████░░  79%                     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Playback ─────────────────────────────────────────────┐  │
│  │  ◀◀  ▶  ▶▶   0.5x ▼                                  │  │
│  │  idle▓▓▓▓▓▓ load░ stride░ swing▓▓ contact● FT▓▓▓▓  │  │
│  │                                    ▲ current frame     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Velocity Loss Events ────────────────────────────────┐  │  │
│  │  ⚠ Frame 162: Wrist decel before contact (-15%)      │  │  │
│  │  ⚠ Frame 38: Hip opening before shoulder load (-8%)  │  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```