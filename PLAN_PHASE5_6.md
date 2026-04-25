# Baseball Swing Analyzer — Phase 5 + Phase 6 Implementation Plan

---

## Phase 5: Web Application

### Goal
Build a clean, modern React web app that lets users upload swing videos, queue them for analysis, and view rich results in a dashboard.

### Design System

**Brand: SWINGMETRICS**
- **Colors:** Slate-900 background, emerald-400 accent, zinc-200 text on dark.
- **Typography:** Inter or Geist Sans (clean, geometric, modern).
- **Vibe:** Dark mode by default, minimal UI, generous whitespace, subtle glassmorphism cards.

**Key Screens**

```
┌────────────────────────────────────────┐
│  📤 Upload Page (Drop Zone)           │
│  ────                                 │
│  [ Drag a swing video here ]          │
│  OR [ Browse files ]                  │
│                                       │
│  Tips: 30–240fps, 5–15 seconds,      │
│  side or back view preferred.         │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Processing Job                        │
│  ────                                 │
│  ● Uploading...                       │
│  ● Detecting hitter...                │
│  ○ Estimating pose (17 keypoints)...  │
│  ○ Computing biomechanical metrics... │
│  ○ Generating coaching report...      │
│                                       │
│  ▼ View Live Logs                     │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Results Dashboard (3-column)          │
│  ────                                 │
│  ┌─ Video Player ─┐ ┌─ Metrics ───┐ │
│  │ [annotated mp4]│ │ ┌─Card────┐ │ │
│  │ scrub bar      │ │ │ Bat Speed│ │ │
│  │ phase labels   │ │ │ 64 mph   │ │ │
│  │ keypoints      │ │ └─────────┘ │ │
│  │ overlay toggle │ │ ┌─Card────┐ │ │
│  │ slo-mo toggle  │ │ │ X-Factor │ │ │
│  └─────────────────┘ │ │ 22°      │ │ │
│                       │ └─────────┘ │ │
│  ┌─ Coaching ───────┐ │ ┌─Card────┐ │ │
│  │ 💡 Front knee    │ │ │ Hip Angle│ │ │
│  │ too straight     │ │ │ 135°     │ │ │
│  │                  │ │ └─────────┘ │ │
│  │ 🎥 Recommended   │ └─────────────┘ │
│  │ drill: Soft      │ ┌─ Charts ───┐  │
│  │ toss with brace  │ │ knee angle │  │
│  │ front leg        │ │ over time  │  │
│  └─────────────────────│ [sparkline]│  │
│                       │ wrist vel  │  │
│                       │ [sparkline]│  │
│                       └──────────────┘  │
└────────────────────────────────────────┘
```

### Frontend Stack
| Layer | Tech | Why |
|-------|------|-----|
| Framework | Next.js 14 (App Router) | React, SSR optional, simple API routes |
| Styling | Tailwind CSS + shadcn/ui | Clean components, consistent design |
| Charts | Recharts or Tremor | React-native charts, easy sparklines |
| Video | Plyr or Vidstack | Custom controls, overlay toggle |
| Animations | Framer Motion | Smooth entrances, progress transitions |
| 3D (Phase 6) | Three.js + React Three Fiber | GPU-accelerated 3D in browser |

### Backend Stack (integrates with existing Python engine)
| Layer | Tech | Why |
|-------|------|-----|
| API | FastAPI | Async, Python-native, easy Pydantic models |
| Job Queue | Celery + Redis | Reliable async processing for long video tasks |
| Storage | Local filesystem MVP → AWS S3 for scale | Videos + outputs must persist |
| Files | `UPLOAD_DIR`, `OUTPUT_DIR` configurable | Same as existing --output flag |

### New Files to Create

```
web/
  ├── next.config.ts
  ├── package.json
  ├── postcss.config.ts
  ├── tailwind.config.ts
  ├── src/
  │   ├── app/
  │   │   ├── layout.tsx          — root shell, dark theme
  │   │   ├── page.tsx            — upload drop-zone
  │   │   ├── job/[id]/page.tsx   — processing + results dashboard
  │   │   └── api/
  │   │       └── jobs/
  │   │           ├── route.ts    — POST upload
  │   │           └── [id]/route.ts  — GET status/results
  │   ├── components/
  │   │   ├── VideoPlayer.tsx     — Plyr with annotated overlay toggle
  │   │   ├── MetricsGrid.tsx     — cards for each metric
  │   │   ├── CoachingReport.tsx  — markdown rendering of coaching.md
  │   │   ├── UploadDropZone.tsx  — drag/drop, accept mp4/mov
  │   │   ├── JobProgress.tsx     — live polling, steps list
  │   │   ├── PhaseBar.tsx        — colored bar showing phase per frame
  │   │   └── KneeAngleChart.tsx   — recharts sparkline
  │   └── lib/
  │       └── api.ts              — fetch wrappers
  server/
  ├── main.py                     — FastAPI entrypoint
  ├── api/
  │   ├── upload.py               — POST /upload, save file, enqueue Celery task
  │   ├── status.py               — GET /job/{id} → status dict
  │   ├── results.py              — GET /job/{id}/results → metrics JSON
  │   └── artifacts.py            — GET /job/{id}/artifacts/{filename}
  └── tasks/
      ├── analyze.py              — Celery task: calls analyze_swing CLI internally
      └── __init__.py
```

### API Contract

```python
# POST /api/jobs
# Body: multipart/form-data with video file
# Response: {"job_id": "uuid", "status": "queued"}

# GET /api/jobs/{job_id}
# Response: {"status": "processing", "progress": 0.6, "current_step": "pose_estimation"}

# GET /api/jobs/{job_id}/results
# Response: metrics dict + flags + coaching report HTML (pre-rendered)

# GET /api/jobs/{job_id}/artifacts/annotated.mp4
# Response: video/mp4 stream
```

### Database Schema (SQLite + SQLAlchemy MVP)

```python
class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    original_filename: Mapped[str]
    video_path: Mapped[str]        # absolute path to uploaded video
    output_dir: Mapped[str]         # absolute path to results/
    status: Mapped[str]             # queued | processing | completed | failed
    progress: Mapped[float]         # 0.0 – 1.0
    metrics_json: Mapped[str|None]  # dumped JSON
    coaching_html: Mapped[str|None]  # pre-rendered coaching report
    created_at: Mapped[datetime]
    completed_at: Mapped[datetime|None]
    error_message: Mapped[str|None]
```

### Phase 5 "Done When"
- User can drag-drop a video and see it queued.
- Progress page auto-refreshes (polling or SSE) until done.
- Results page shows: annotated video, metrics cards, coaching report, phase bar.
- Backend serves artifacts via static file URL.
- Mobile responsive.
- End-to-end upload→results in <2 mins for a 10-second 1080p video.

---

## Phase 6: 3D Batter Visualization + Physics Overlay

### Goal
Take the existing 2D pose keypoints (17 COCO) and render an animated 3D skeleton showing the swing in slow motion, with velocity vectors and efficiency heatmaps.

### Why This Is Hard
- Current data is **2D** (x, y, confidence). True 3D requires depth.
- **Mitigation 1:** Simple kinematic lifting from 2D + known body proportions (bone lengths) → approximate 3D positions. Good enough for visual impact.
- **Mitigation 2:** For true 3D, integrate CLIFF (Phase 2.5) or just animate the skeleton in a fixed viewing plane.

### Approach: 3-Pronged

| Approach | Effort | Cool Factor | Accuracy |
|----------|--------|-------------|----------|
| **A. 2.5D Skeleton** (Three.js) | 2 days | ⭐⭐⭐ | Medium — stick figure with depth approximated from bone-length ratios. |
| **B. Physics Overlay** (velocity vectors, force arrows) | 1 day | ⭐⭐⭐⭐ | N/A — math from existing metrics. |
| **C. True 3D** (CLIFF → world coords → Three.js) | 1 week | ⭐⭐⭐⭐⭐ | High — Phase 2.5 dependency. |

**MVP:** Build A + B first. Add C as Phase 6.5 if needed.

### Visual Design for 3D Scene

```
Dark environment (slate-900 bg)
  │
  ├─ Ground plane: subtle baseball-field lines (batter's box, home plate)
  │
  ├─ Skeleton (Three.js TubeGeometry or Lines)
  │    │  Color: neon emerald for body, neon amber for bat proxy
  │    │  Size: proportional to real human (1.8m tall)
  │    │
  │    ├─ Phase scrub bar (bottom)
  │    │     user drags to scrub through swing
  │    │
  │    ├─ Velocity Arrows (animated)
  │    │     hip rotation arrow (green, thick) = power source
  │    │     wrist velocity arrow (amber, thin) = bat speed proxy
  │    │     head movement arrow (red, dashed) = instability
  │    │
  │    ├─ Heatmap Overlay (transparent sphere at joints)
  │    │     red = high kinetic-chain efficiency (energy transfer good)
  │    │     blue = low efficiency (energy lost, e.g., collapsing knee)
  │    │
  │    └─ Ghost Trail (opacity trail of bat/wrist path)
  │           shows swing plane arc over last 15 frames
  │
  └─ Physics Panel (right side, overlaid)
       ┌─ Bat Speed: 63 mph ▼ (lost 12mph vs MLB avg)
       ┌─ Hip Rotation: 520°/s ▲ (good)
       ┌─ Energy Leak: Front knee collapse (highlighted on skeleton)
       └─ Contact Point: +0.2 ft deep (late contact)
```

### Three.js Implementation Plan

**Prerequisites:** Export data from Python → JSON consumable by Three.js.

New file: `web/src/components/Swing3D.tsx`

```typescript
interface Frame3D {
  keypoints: [x: number, y: number, z: number][]; // 17 keypoints
  phase: string;
  wristSpeed: number;      // px/s → mapped to arrow scale
  hipRotationSpeed: number; // deg/s → mapped
}

interface Swing3DProps {
  frames: Frame3D[];
  fps: number;
}
```

**Skeleton Construction:**
1. For each frame, map 17 keypoints to joint positions.
2. Create `THREE.Line` or `THREE.TubeGeometry` connections using COCO_PAIRS.
3. Color joints by phase (stance=blue, load=amber, swing=emerald, contact=red).
4. Animate by swapping vertex positions per frame (or lerping between frames for smoothness).

**Velocity Arrows:**
- `THREE.ArrowHelper` placed at hip center, wrist center, shoulder center.
- Direction = vector from current frame to next frame.
- Length = scaled velocity magnitude.
- Color = green (good) → amber (medium) → red (bad) based on metric thresholds.

**Heatmap Overlay:**
- `THREE.SphereGeometry` at each joint.
- Opacity = 0.0–0.6 based on "kinetic chain efficiency" (a metric we'll compute).
- Color = `THREE.Color.lerpColors(emerald, red, efficiency_score)`.

**Ghost Trail:**
- `THREE.BufferGeometry` with `Line` strip for wrist trajectory over last 15 frames.
- Color fades from opaque (recent) to transparent (old).

### New Python Metric for 3D Phase

```python
# metrics.py

def kinetic_chain_efficiency(keypoints_seq: np.ndarray) -> np.ndarray:
    """Per-frame efficiency score: how well energy transfers hip→shoulder→wrist.

    High = hips rotate before shoulders, shoulders before wrists.
    Low = everything fires at once (muscling) or wrong order (casting).
    """
    ...
```

### New Pipeline Step (Phase 6)

```
analyze_swing() now also calls:
    from .visualizer_3d import generate_swing_3d_data
    report["frames_3d"] = generate_swing_3d_data(keypoints_seq, fps, phase_labels)
```

Generates `frames_3d.json` (same structure as `Frame3D` interface above).

### Phase 6 "Done When"
- User can scrub through the swing in a 3D scene.
- Velocity arrows grow/shrink dynamically.
- Ghost trail shows swing plane arc.
- Heatmap highlights inefficiencies visually.
- Scene rotates with mouse drag; zoom with scroll.
- Physics panel updates in sync with 3D scrub.

---

## Combined Build Order (Phase 5 + Phase 6)

| Week | Task | Files | Deliverable |
|------|------|-------|-------------|
| 1 | FastAPI scaffold + Celery + upload API | `server/` | `curl -F video=@swing.mp4 localhost:8000/upload` returns job_id |
| 1 | Next.js scaffold + dark theme + shadcn | `web/` | `npm run dev`, blank dark page visible |
| 2 | Upload drop-zone + job progress + polling | `web/src/app/page.tsx`, `JobProgress.tsx` | working upload UI |
| 2 | Celery task wired to existing `analyze_swing` | `server/tasks/analyze.py` | API returns `processing` then `completed` |
| 3 | Results dashboard: video player + metrics cards | `web/src/app/job/[id]/page.tsx`, `MetricsGrid.tsx` | rich results page |
| 3 | Coaching report rendered from markdown | `CoachingReport.tsx` | clean coaching cards |
| 4 | Three.js scene: 2.5D skeleton + basic animation | `Swing3D.tsx` | can see stick figure swing |
| 4 | Velocity arrows + ghost trail | `Swing3D` extensions | looks impressive |
| 5 | Heatmap + kinetic chain efficiency metric | `metrics.py` update + Three.js overlay | physics overlay working |
| 5 | Phase scrub bar + physics panel | `PhaseBar.tsx` + sync to 3D | interactive and polished |
| 6 | True 3D (optional Phase 6.5) | CLIFF integration if needed | full world-coordinate 3D |

---

## Tech Summary

**Phase 5 Only:**
- Python: FastAPI, Celery, Redis, SQLAlchemy, uvicorn
- JS: Next.js, Tailwind, shadcn/ui, Recharts
- Dev: separate frontend (`web/`) and backend (`server/`), both run locally

**Phase 6 Only (adds):**
- JS: `@react-three/fiber`, `@react-three/drei`, Three.js
- Python: `generate_swing_3d_data()` exporter in existing pipeline

---

## Risk Register

| # | Risk | Mitigation |
|---|------|------------|
| 1 | Next.js requires Node 18+; user may not have it | Document install, provide `nvm use` command |
| 2 | Celery + Redis setup on Windows is painful | Provide Docker Compose, or use FastAPI `BackgroundTasks` for MVP |
| 3 | Three.js bundle size large | Code-split `Swing3D` component; lazy load |
| 4 | 2.5D skeleton may look disappointing | Polish with post-processing bloom, glow, motion blur |
| 5 | Video files large (10–100MB) | Implement chunked upload or presigned S3 URL |

---

## Single Command to Launch Everything

```bash
# Terminal 1 — backend
cd server
pip install -e ".[web]"    # new extra deps: fastapi, celery, redis, uvicorn
redis-server &
celery -A tasks worker --loglevel=info &
python -m uvicorn main:app --reload

# Terminal 2 — frontend
cd web
npm install       # or pnpm install
npm run dev
```

Then open `http://localhost:3000`.
