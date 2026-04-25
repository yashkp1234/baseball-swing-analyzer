import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid, PerspectiveCamera } from "@react-three/drei";
import { type Swing3DData } from "@/lib/api";
import { BatterFigure } from "@/components/three/BatterFigure";
import { VelocityArrows } from "@/components/three/VelocityArrows";
import { EnergyLossMarker } from "@/components/three/EnergyLossMarker";
import { KineticChainRings } from "@/components/three/KineticChainRings";
import { Card, CardTitle } from "@/components/Card";
import { ArrowLeft } from "lucide-react";
import { Slider } from "@/components/ui/Slider";

const TRAIL_LENGTH = 15;

const PHASE_COLORS: Record<string, string> = {
  idle: "#555555", stance: "#4A90D9", load: "#00CC6A", stride: "#D4A017",
  swing: "#00FF87", contact: "#FFD700", follow_through: "#FF8A00",
};

export function SwingViewerPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const location = useLocation();
  const data = (location.state as { data?: { frames_3d?: Swing3DData } })?.data?.frames_3d as Swing3DData | undefined;
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);

  useEffect(() => {
    if (!data || !isPlaying) return;
    const id = setInterval(() => {
      setCurrentFrame((prev) => (prev >= data.total_frames - 1 ? 0 : prev + 1));
    }, 1000 / (data.fps * speed));
    return () => clearInterval(id);
  }, [isPlaying, data, speed]);

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <p className="text-[var(--color-red)]">No 3D data available. Go back to results and try again.</p>
          <Link to={jobId ? `/results/${jobId}` : "/"} className="mt-4 inline-block text-[var(--color-accent)] hover:underline">Back to Results</Link>
        </Card>
      </div>
    );
  }

  const frame = data.frames[currentFrame] ?? data.frames[0];
  const trailStart = Math.max(0, currentFrame - TRAIL_LENGTH);
  const trailFrames = data.frames.slice(trailStart, currentFrame);
  const bodyCenter: [number, number, number] = [0, 0, 0];
  if (frame) {
    const lh = frame.keypoints[11] ?? [0, 0, 0];
    const rh = frame.keypoints[12] ?? [0, 0, 0];
    bodyCenter[0] = ((lh[0] ?? 0) + (rh[0] ?? 0)) / 2;
    bodyCenter[1] = ((lh[1] ?? 0) + (rh[1] ?? 0)) / 2;
    bodyCenter[2] = ((lh[2] ?? 0) + (rh[2] ?? 0)) / 2;
  }

  const eventsInRange = data.energy_loss_events
    .filter((e) => Math.abs(e.frame - currentFrame) < 3)
    .map((e) => {
      const f = data.frames[e.frame] ?? frame;
      const names = data.keypoint_names;
      const idx = names.indexOf(e.joint === "right_wrist" ? "right_wrist" : e.joint === "hip_center" ? "right_hip" : e.joint.replace("_", "") );
      const kp = idx >= 0 ? f.keypoints[idx] : [0, 0, 0];
      return { ...e, position: kp as [number, number, number] };
    });

  const currentPhase = frame?.phase ?? "idle";

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex flex-col">
      <header className="border-b border-[var(--color-border)] px-6 py-3 flex items-center justify-between">
        <Link to={`/results/${jobId}`} className="flex items-center gap-2 text-[var(--color-text-dim)] hover:text-[var(--color-text)]">
          <ArrowLeft className="h-4 w-4" /><span className="text-sm">Back to Results</span>
        </Link>
        <h1 className="text-lg font-semibold">3D <span className="text-[var(--color-accent)]">Swing</span> Viewer</h1>
        <div className="w-24" />
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-0">
        <div className="relative bg-[var(--color-bg)]">
          <Canvas shadows style={{ minHeight: "500px" }}>
            <PerspectiveCamera makeDefault position={[0, 0, 3]} fov={50} />
            <OrbitControls enableDamping dampingFactor={0.1} />
            <ambientLight intensity={0.6} />
            <directionalLight position={[5, 5, 5]} intensity={0.8} />
            <Grid args={[10, 10]} position={[0, -1, 0]} cellColor="#222" sectionColor="#333" fadeDistance={8} />
            {frame && <BatterFigure frame={frame} trailFrames={trailFrames} />}
            {frame && <VelocityArrows frame={frame} />}
            {eventsInRange.map((e, i) => <EnergyLossMarker key={i} position={e.position} severity={e.magnitude_pct} description={e.description} />)}
            <KineticChainRings hipScore={data.kinetic_chain_scores.hip_to_shoulder} shoulderScore={data.kinetic_chain_scores.shoulder_to_hand} overallScore={data.kinetic_chain_scores.overall} center={bodyCenter} />
          </Canvas>
        </div>

        <div className="border-l border-[var(--color-border)] bg-[var(--color-surface)] p-4 space-y-4 overflow-y-auto">
          <Card>
            <CardTitle>Kinetic Chain Efficiency</CardTitle>
            <EfficiencyBar label="Hip → Shoulder" value={data.kinetic_chain_scores.hip_to_shoulder} />
            <EfficiencyBar label="Shoulder → Hand" value={data.kinetic_chain_scores.shoulder_to_hand} />
            <EfficiencyBar label="Overall" value={data.kinetic_chain_scores.overall} />
          </Card>

          {data.energy_loss_events.length > 0 && (
            <Card>
              <CardTitle>Energy Loss Events</CardTitle>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {data.energy_loss_events.slice(0, 8).map((e, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm cursor-pointer hover:bg-[var(--color-surface-2)] rounded p-1 -mx-1" onClick={() => setCurrentFrame(e.frame)}>
                    <span className="text-[var(--color-red)] mt-0.5">⚠</span>
                    <div>
                      <p className="text-[var(--color-text)]">Frame {e.frame}: {e.description}</p>
                      <p className="text-xs text-[var(--color-text-dim)]">{e.type} · {e.magnitude_pct}% loss</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card>
            <CardTitle>Current Frame</CardTitle>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-[var(--color-text-dim)]">Frame</div><div className="text-[var(--color-text)] font-mono">{currentFrame}</div>
              <div className="text-[var(--color-text-dim)]">Phase</div>
              <div style={{ color: PHASE_COLORS[currentPhase] }}>{currentPhase}</div>
              <div className="text-[var(--color-text-dim)]">Efficiency</div><div className="text-[var(--color-text)] font-mono">{(frame?.efficiency ?? 0).toFixed(2)}</div>
            </div>
          </Card>
        </div>
      </div>

      <div className="border-t border-[var(--color-border)] p-4">
        <div className="flex items-center gap-4">
          <button onClick={() => setIsPlaying(!isPlaying)} className="w-10 h-10 rounded-full bg-[var(--color-accent)] text-[var(--color-bg)] flex items-center justify-center font-bold text-lg hover:brightness-110">
            {isPlaying ? "⏸" : "▶"}
          </button>
          <div className="flex-1">
            <Slider min={0} max={data.total_frames - 1} value={currentFrame} onChange={setCurrentFrame} />
          </div>
          <div className="flex items-center gap-2">
            {[0.25, 0.5, 1, 2].map((s) => (
              <button key={s} onClick={() => setSpeed(s)} className={`px-2 py-0.5 rounded text-xs ${speed === s ? "bg-[var(--color-accent)] text-[var(--color-bg)]" : "bg-[var(--color-surface-2)] text-[var(--color-text-dim)]"}`}>{s}x</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function EfficiencyBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "bg-[var(--color-accent)]" : pct >= 60 ? "bg-[var(--color-amber)]" : "bg-[var(--color-red)]";
  return (
    <div className="mb-2">
      <div className="flex justify-between text-sm mb-1"><span className="text-[var(--color-text-dim)]">{label}</span><span className="text-[var(--color-text)] font-mono">{pct}%</span></div>
      <div className="h-2 rounded-full bg-[var(--color-surface-2)] overflow-hidden"><div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} /></div>
    </div>
  );
}