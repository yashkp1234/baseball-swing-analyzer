import { useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

interface KineticChainRingsProps {
  hipScore: number;
  shoulderScore: number;
  overallScore: number;
  center: [number, number, number];
}

export function KineticChainRings({ hipScore, shoulderScore, overallScore, center }: KineticChainRingsProps) {
  const hipRef = useRef<THREE.Mesh>(null);
  const shoulderRef = useRef<THREE.Mesh>(null);
  const handRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    [hipRef, shoulderRef, handRef].forEach((ref, i) => {
      if (!ref.current) return;
      const sc = ref.current.scale.x;
      const target = 0.3 + Math.sin(t * 2 + i * 1.5) * 0.02;
      ref.current.scale.setScalar(target);
    });
  });

  return (
    <group position={center}>
      <mesh ref={hipRef} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.18, 0.005, 8, 32]} />
        <meshStandardMaterial
          color="#4A90D9"
          emissive="#4A90D9"
          emissiveIntensity={hipScore * 0.5}
          transparent
          opacity={0.4 + hipScore * 0.4}
        />
      </mesh>
      <mesh ref={shoulderRef} rotation={[Math.PI / 2, 0, 0]} position={[0, 0.05, 0]}>
        <torusGeometry args={[0.15, 0.004, 8, 32]} />
        <meshStandardMaterial
          color="#D4A017"
          emissive="#D4A017"
          emissiveIntensity={shoulderScore * 0.5}
          transparent
          opacity={0.4 + shoulderScore * 0.4}
        />
      </mesh>
      <mesh ref={handRef} rotation={[Math.PI / 2, 0, 0]} position={[0, 0.1, 0]}>
        <torusGeometry args={[0.12, 0.003, 8, 32]} />
        <meshStandardMaterial
          color="#00FF87"
          emissive="#00FF87"
          emissiveIntensity={overallScore * 0.5}
          transparent
          opacity={0.4 + overallScore * 0.4}
        />
      </mesh>
    </group>
  );
}