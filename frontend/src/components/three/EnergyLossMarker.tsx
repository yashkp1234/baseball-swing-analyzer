import { useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

interface EnergyLossMarkerProps {
  position: [number, number, number];
  severity: number;
  description: string;
}

export function EnergyLossMarker({ position, severity }: EnergyLossMarkerProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const pulseScale = Math.min(severity / 50, 1.5) * 0.04 + 0.02;

  useFrame((state) => {
    if (!meshRef.current) return;
    const t = state.clock.getElapsedTime();
    const pulse = 1 + Math.sin(t * 4) * 0.3;
    meshRef.current.scale.setScalar(pulseScale * pulse);
  });

  return (
    <group position={position}>
      <mesh ref={meshRef}>
        <sphereGeometry args={[1, 16, 12]} />
        <meshStandardMaterial
          color="#FF4444"
          emissive="#FF4444"
          emissiveIntensity={0.6}
          transparent
          opacity={0.7}
        />
      </mesh>
      <pointLight color="#FF4444" intensity={0.3 * (severity / 15)} distance={0.3} />
    </group>
  );
}