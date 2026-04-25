import { useMemo } from "react";
import * as THREE from "three";
import type { Frame3D } from "./types";

interface VelocityArrowsProps {
  frame: Frame3D;
  scale?: number;
}

const VELOCITY_JOINTS = [
  { name: "right_wrist", joint: 10, color: "#00FF87" },
  { name: "left_wrist", joint: 9, color: "#00CC6A" },
  { name: "hip_center", joint: 11, color: "#4A90D9" },
  { name: "shoulder_center", joint: 5, color: "#D4A017" },
];

function ArrowHelper({ origin, direction, length, color }: {
  origin: THREE.Vector3;
  direction: THREE.Vector3;
  length: number;
  color: string;
}) {
  const shaftLen = length * 0.75;
  const headLen = length * 0.25;
  const headRadius = headLen * 0.4;

  return (
    <group position={origin}>
      <group rotation={new THREE.Euler().setFromVector3(direction, "XYZ")}>
        {/* Shaft */}
        <mesh position={[0, shaftLen / 2, 0]}>
          <cylinderGeometry args={[0.004, 0.004, shaftLen, 6]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
        </mesh>
        {/* Head */}
        <mesh position={[0, shaftLen + headLen / 2, 0]}>
          <coneGeometry args={[headRadius, headLen, 6]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
        </mesh>
      </group>
    </group>
  );
}

export function VelocityArrows({ frame, scale = 0.003 }: VelocityArrowsProps) {
  const arrows = useMemo(() => {
    const result: {
      origin: THREE.Vector3;
      dir: THREE.Vector3;
      length: number;
      color: string;
    }[] = [];

    for (const vj of VELOCITY_JOINTS) {
      const vec = frame.velocity_vectors?.[vj.name];
      const speed = frame.velocities[vj.name];
      if (!vec || !speed || speed < 10) continue;

      const origin = new THREE.Vector3(
        frame.keypoints[vj.joint]?.[0] ?? 0,
        frame.keypoints[vj.joint]?.[1] ?? 0,
        frame.keypoints[vj.joint]?.[2] ?? 0,
      );

      const direction = new THREE.Vector3(vec[0], vec[1], vec[2] || 0);
      const vecLen = direction.length();
      if (vecLen < 0.01) continue;
      direction.normalize();

      const arrowLen = Math.min(speed * scale, 0.5);
      result.push({ origin, dir: direction, length: arrowLen, color: vj.color });
    }

    return result;
  }, [frame, scale]);

  return (
    <group>
      {arrows.map((a, i) => (
        <ArrowHelper
          key={`va-${i}`}
          origin={a.origin}
          direction={a.dir}
          length={a.length}
          color={a.color}
        />
      ))}
    </group>
  );
}