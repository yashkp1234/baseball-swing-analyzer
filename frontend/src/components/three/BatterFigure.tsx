import { useMemo } from "react";
import * as THREE from "three";
import { Line } from "@react-three/drei";
import type { Frame3D } from "./types";

const SKELETON_EDGES: [number, number][] = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12],
  [11, 13], [13, 15], [12, 14], [14, 16],
  [0, 5], [0, 6],
];

const PHASE_COLORS: Record<string, string> = {
  idle: "#555555",
  stance: "#4A90D9",
  load: "#00CC6A",
  stride: "#D4A017",
  swing: "#00FF87",
  contact: "#FFD700",
  follow_through: "#FF8A00",
};

interface BatterFigureProps {
  frame: Frame3D;
  showTrail?: boolean;
  trailFrames?: Frame3D[];
}

export function BatterFigure({ frame, showTrail = true, trailFrames = [] }: BatterFigureProps) {
  const phaseColor = PHASE_COLORS[frame.phase] || "#555555";

  const joints = useMemo(() => {
    return frame.keypoints.map((kp) => {
      const x = kp[0] ?? 0;
      const y = kp[1] ?? 0;
      const z = kp[2] ?? 0;
      return new THREE.Vector3(x, y, z);
    });
  }, [frame]);

  const ghostPositions = useMemo(() => {
    if (!showTrail || trailFrames.length === 0) return [];
    const wrists = [9, 10];
    return trailFrames.map((f, idx) => {
      const opacity = (idx + 1) / trailFrames.length;
      return wrists.map(w => ({
        pos: new THREE.Vector3(f.keypoints[w][0], f.keypoints[w][1], f.keypoints[w][2]),
        opacity,
      }));
    }).flat();
  }, [trailFrames, showTrail]);

  return (
    <group>
      {/* Joint spheres */}
      {joints.map((pos, i) => {
        const isEndJoint = [9, 10, 15, 16].includes(i);
        return (
          <mesh key={`j-${i}`} position={pos}>
            <sphereGeometry args={[isEndJoint ? 0.03 : 0.02, 12, 8]} />
            <meshStandardMaterial
              color={isEndJoint ? phaseColor : "#cccccc"}
              emissive={isEndJoint ? phaseColor : "#000000"}
              emissiveIntensity={isEndJoint ? 0.3 : 0}
            />
          </mesh>
        );
      })}

      {/* Skeleton lines */}
      {SKELETON_EDGES.map(([a, b], idx) => {
        if (!joints[a] || !joints[b]) return null;
        return (
          <Line
            key={`s-${idx}`}
            points={[joints[a], joints[b]]}
            color={phaseColor}
            lineWidth={2}
            opacity={0.8}
          />
        );
      })}

      {/* Ghost trail for wrists */}
      {ghostPositions.map((gp, i) => (
        <mesh key={`ghost-${i}`} position={gp.pos}>
          <sphereGeometry args={[0.015, 8, 4]} />
          <meshBasicMaterial color="#00FF87" transparent opacity={gp.opacity * 0.4} />
        </mesh>
      ))}
    </group>
  );
}
