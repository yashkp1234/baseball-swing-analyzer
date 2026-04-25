import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid, PerspectiveCamera } from "@react-three/drei";
import { getJobResults, artifactUrl, type Swing3DData } from "@/lib/api";
import { BatterFigure } from "@/components/three/BatterFigure";
import { VelocityArrows } from "@/components/three/VelocityArrows";
import { EnergyLossMarker } from "@/components/three/EnergyLossMarker";
import { KineticChainRings } from "@/components/three/KineticChainRings";
import { PlaybackControls } from "@/components/three/PlaybackControls";
import { Card, CardTitle } from "@/components/Card";
import { ArrowLeft } from "lucide-react";

const TRAIL_LENGTH = 15;

export function SwingViewerPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [data, setData] = useState<Swing3DData | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const nextFrameRef = useRef(0);

  useEffect(() => {
    if (!jobId) return;
    getJobResults(jobId).then((r) => {
      if (r.frames_3d) setData(r.frames_3d as Swing3DData);
    });
  }, [jobId]);

  const animate = useCallback(() => {
    if (!data || !isPlaying) return;
    const interval = 1000 / (data.fps * speed);
    nextFrameRef.current += interval;
    const next = (nextFrameRef.current / 1000) * data.fps * speed;
    setCurrentFrame((prev) => {
      if (prev >= data.total_frames - 1) return 0;
      return Math.min(prev + 1, data.total_frames - 1);
    });
  }, [data, isPlaying, speed]);

  useEffect(() => {
    if (!isPlaying || !data) return;
    const id = setInterval(() => {
      setCurrentFrame((prev) => {
        if (prev >= data.total_frames - 1) return 0;
        return prev + 1;
      });
    }, 1000 / (data.fps * speed));
    return () => clearInterval(id);
  }, [isPlaying, data, speed]);

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-[var(--color-text-dim)]">Loading 3D data...</div>
      </div>
    );
  }

  const frame = data.frames[currentFrame] ?? data.frames[0];
  const trailStart = Math.max(0, currentFrame - TRAIL_LENGTH);
  const trailFrames = data.frames.slice(trailStart, currentFrame);

  const hipCenter = [11, 12];
  const bodyCenter: [number, number, number] = [0, 0, 0];
  if (frame) {
    const lhip = frame.keypoints[11] ?? [0, 0, 0];
    const rhip = frame.keypoints[12] ?? [0, 0, 0];
    bodyCenter[0] = (lhip[0] + rhip[0]) / 2;
    bodyCenter[1] = (lhip[1] + rhip[1]) / 2;
    bodyCenter[2] = ((lhip[2] ?? 0) + (rhip[2] ?? 0)) / 2;
  }

  const eventsInRange = data.energy_loss_events
    .filter((e) => Math.abs(e.frame - currentFrame) < 3)
    .map((e) => {
      const f = data.frames[e.frame] ?? frame;
      const jointIdx = data.keypoint_names.indexOf(e.joint.replace("_", "").includes("wrist") ? (e.joint.startsWith("right") ? "right_wrist" : "left_wrist") : "hip_center");
      const kp = jointIdx >= 0 ? f.keypoints[jointIdx] : [0, 0, 0];
      return { ...e, position: kp as [number, number, number] };
    });

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex flex-col">
      <header className="border-b border-[var(--color-border)] px-6 py-3 flex items-center justify-between">
        <Link to={`/results/${jobId}`} className="flex items-center gap-2 text-[var(--color-text-dim)] hover:text-[var(--color-text)]">
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">Back to Results</span>
        </Link>
        <h1 className="text-lg font-semibold">
          3D <span className="text-[var(--color-accent)]">Swing</span> Viewer
        </h1>
        <div className="w-24" />
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-0">
        {/* 3D Canvas */}
        <div className="relative bg-[var(--color-bg)]">
          <Canvas shadows className="w-full h-full" style={{ minHeight: "500px" }}>
            <PerspectiveCamera makeDefault position={[0, 0, 3]} fov={50} />
            <OrbitControls enableDamping dampingFactor={0.1} />
            <ambientLight intensity={0.6} />
            <directionalLight position={[5, 5, 5]} intensity={0.8} castShadow />
            <Grid
              args={[10, 10]}
              position={[0, -1, 0]}
              cellColor="#222"
              sectionColor="#333"
              fadeDistance={8}
              fadeStrength={1.5}
            />
            {frame && <BatterFigure frame={frame} trailFrames={trailFrames} />}
            {frame && <VelocityArrows frame={frame} />}
            {eventsInRange.map((e, i) => (
              <EnergyLossMarker
                key={`el-${i}`}
                position={e.position}
                severity={e.magnitude_pct}
                description={e.description}
              />
            ))}
            <KineticChainRings
              hipScore={data.kinetic_chain_scores.hip_to_shoulder}
              shoulderScore={data.kinetic_chain_scores.shoulder_to_hand}
              overallScore={data.kinetic_chain_scores.overall}
              center={bodyCenter}
            />
          </Canvas>
        </div>

        {/* Side Panel */}
        <div className="border-l border-[var(--color-border)] bg-[var(--color-surface)] p-4 space-y-4 overflow-y-auto">
          <Card>
            <CardTitle>Kinetic Chain Efficiency</CardTitle>
            <div className="space-y-3">
              <EfficiencyBar
                label="Hip → Shoulder"
                value={data.kinetic_chain_scores.hip_to_shoulder}
              />
              <EfficiencyBar
                label="Shoulder → Hand"
                value={data.kinetic_chain_scores.shoulder_to_hand}
              />
              <EfficiencyBar
                label="Overall"
                value={data.kinetic_chain_scores.overall}
              />
            </div>
          </Card>

          {data.energy_loss_events.length > 0 && (
            <Card>
              <CardTitle>Energy Loss Events</CardTitle>
              <div className="space-y-2">
                {data.energy_loss_events.slice(0, 8).map((e, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 text-sm cursor-pointer hover:bg-[var(--color-surface-2)] rounded p-1 -mx-1"
                    onClick={() => setCurrentFrame(e.frame)}
                  >
                    <span className="text-[var(--color-red)] mt-0.5">⚠</span>
                    <div>
                      <p className="text-[var(--color-text)]">
                        Frame {e.frame}: {e.description}
                      </p>
                      <p className="text-xs text-[var(--color-text-dim)]">
                        {e.type} · {e.magnitude_pct}% velocity loss
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card>
            <CardTitle>Current Frame</CardTitle>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-[var(--color-text-dim)]">Frame</div>
              <div className="text-[var(--color-text)] font-mono">{currentFrame}</div>
              <div className="text-[var(--color-text-dim)]">Phase</div>
              <div className="text-[var(--color-text)]">{frame?.phase}</div>
              <div className="text-[var(--color-text-dim)]">Efficiency</div>
              <div className="text-[var(--color-text)] font-mono">{(frame?.efficiency ?? 0).toFixed(2)}</div>
            </div>
          </Card>
        </div>
      </div>

      {/* Playback Controls */}
      <div className="border-t border-[var(--color-border)] p-4">
        <PlaybackControls
          currentFrame={currentFrame}
          totalFrames={data.total_frames}
          fps={data.fps}
          isPlaying={isPlaying}
          speed={speed}
          onFrameSelect={setCurrentFrame}
          onPlayPause={() => setIsPlaying(!isPlaying)}
          onSpeedChange={setSpeed}
          phaseLabels={data.phase_labels}
          contactFrame={data.contact_frame}
        />
      </div>
    </div>
  );
}

function EfficiencyBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "bg-[var(--color-accent)]" : pct >= 60 ? "bg-[var(--color-amber)]" : "bg-[var(--color-red)]";
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-[var(--color-text-dim)]">{label}</span>
        <span className="text-[var(--color-text)] font-mono">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}