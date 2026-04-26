import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { Swing3DData } from "@/lib/api";

interface Props {
  data: Swing3DData;
  currentFrame: number;
  projected?: boolean;
  resetToken?: number;
  onError?: (message: string | null) => void;
}

const JOINT_RADIUS = 0.028;
const BASELINE_COLOR = "#00ff87";
const PROJECTED_COLOR = "#ffd54a";

export function SwingSkeletonViewer({ data, currentFrame, projected = false, resetToken = 0, onError }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const jointsRef = useRef<THREE.Mesh[]>([]);
  const bonesRef = useRef<THREE.Line[]>([]);
  const batRef = useRef<THREE.Line | null>(null);
  const ballRef = useRef<THREE.Mesh | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const cleanup = () => {
      if (animationFrameRef.current != null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      controlsRef.current?.dispose();
      rendererRef.current?.dispose();
      if (rendererRef.current?.domElement.parentElement === mount) {
        mount.removeChild(rendererRef.current.domElement);
      }
      jointsRef.current = [];
      bonesRef.current = [];
      batRef.current = null;
      ballRef.current = null;
      rendererRef.current = null;
      cameraRef.current = null;
      controlsRef.current = null;
    };

    cleanup();

    try {
      const scene = new THREE.Scene();
      scene.background = new THREE.Color("#05070b");

      const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
      camera.position.set(0.8, 0.55, 2.4);
      camera.lookAt(0, 0, 0);
      cameraRef.current = camera;

      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      rendererRef.current = renderer;
      mount.appendChild(renderer.domElement);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.minDistance = 1.2;
      controls.maxDistance = 4.5;
      controls.target.set(0, 0.05, 0);
      controls.update();
      controlsRef.current = controls;

      scene.add(new THREE.AmbientLight("#dbeafe", 1.2));
      const keyLight = new THREE.DirectionalLight("#ffffff", 1.15);
      keyLight.position.set(1.4, 2.2, 2.6);
      scene.add(keyLight);
      const rimLight = new THREE.DirectionalLight("#60a5fa", 0.45);
      rimLight.position.set(-2.0, 1.4, -1.2);
      scene.add(rimLight);

      const grid = new THREE.GridHelper(3.5, 12, "#143e2b", "#10202c");
      grid.position.y = -0.92;
      scene.add(grid);

      const axes = new THREE.AxesHelper(0.5);
      axes.position.set(-1.15, -0.7, 0.95);
      scene.add(axes);

      const jointMaterial = new THREE.MeshStandardMaterial({
        color: projected ? PROJECTED_COLOR : BASELINE_COLOR,
        emissive: projected ? "#6b4b00" : "#05311f",
        roughness: 0.25,
        metalness: 0.05,
      });
      const jointGeometry = new THREE.SphereGeometry(JOINT_RADIUS, 16, 16);

      jointsRef.current = data.keypoint_names.map(() => {
        const mesh = new THREE.Mesh(jointGeometry, jointMaterial.clone());
        scene.add(mesh);
        return mesh;
      });

      bonesRef.current = data.skeleton.map(() => {
        const geometry = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0, 0),
          new THREE.Vector3(0, 0, 0),
        ]);
        const material = new THREE.LineBasicMaterial({
          color: projected ? PROJECTED_COLOR : BASELINE_COLOR,
          transparent: true,
          opacity: projected ? 0.95 : 0.8,
        });
        const line = new THREE.Line(geometry, material);
        scene.add(line);
        return line;
      });

      const batGeometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 0, 0),
      ]);
      const batMaterial = new THREE.LineBasicMaterial({
        color: "#f5d36b",
        transparent: true,
        opacity: 0.95,
      });
      const batLine = new THREE.Line(batGeometry, batMaterial);
      scene.add(batLine);
      batRef.current = batLine;

      const ball = new THREE.Mesh(
        new THREE.SphereGeometry(0.035, 16, 16),
        new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 0.35 }),
      );
      scene.add(ball);
      ballRef.current = ball;

      const resize = () => {
        const width = Math.max(mount.clientWidth, 1);
        const height = Math.max(mount.clientHeight, 1);
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
      };
      resize();

      const observer = new ResizeObserver(resize);
      observer.observe(mount);

      const animate = () => {
        animationFrameRef.current = requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
      };
      animate();
      onError?.(null);

      return () => {
        observer.disconnect();
        cleanup();
      };
    } catch (error) {
      onError?.(error instanceof Error ? error.message : "3D viewer failed to initialize");
      return undefined;
    }
  }, [data.keypoint_names, data.skeleton, onError, projected]);

  useEffect(() => {
    controlsRef.current?.reset();
  }, [resetToken]);

  useEffect(() => {
    const frame = data.frames[Math.min(currentFrame, data.frames.length - 1)];
    if (!frame) return;

    jointsRef.current.forEach((joint, index) => {
      const point = frame.keypoints[index];
      if (!point || point.length < 3 || point.some((value) => !Number.isFinite(value))) {
        joint.visible = false;
        return;
      }
      joint.visible = true;
      joint.position.set(point[0], point[1], point[2]);
    });

    bonesRef.current.forEach((bone, index) => {
      const [startIndex, endIndex] = data.skeleton[index];
      const start = frame.keypoints[startIndex];
      const end = frame.keypoints[endIndex];
      if (!start || !end || start.some((value) => !Number.isFinite(value)) || end.some((value) => !Number.isFinite(value))) {
        bone.visible = false;
        return;
      }
      const positions = new Float32Array([
        start[0], start[1], start[2],
        end[0], end[1], end[2],
      ]);
      bone.visible = true;
      bone.geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      bone.geometry.computeBoundingSphere();
    });

    const bat = frame.bat;
    if (batRef.current) {
      if (bat && bat.handle.length >= 3 && bat.barrel.length >= 3) {
        batRef.current.visible = true;
        batRef.current.geometry.setAttribute(
          "position",
          new THREE.BufferAttribute(new Float32Array([...bat.handle.slice(0, 3), ...bat.barrel.slice(0, 3)]), 3),
        );
        batRef.current.geometry.computeBoundingSphere();
      } else {
        batRef.current.visible = false;
      }
    }

    const ballPosition = data.ball?.contact_position;
    if (ballRef.current && ballPosition && ballPosition.length >= 3) {
      const contactFrame = data.ball?.contact_frame ?? currentFrame;
      ballRef.current.visible = Math.abs(currentFrame - contactFrame) <= 4;
      ballRef.current.position.set(ballPosition[0], ballPosition[1], ballPosition[2]);
    } else if (ballRef.current) {
      ballRef.current.visible = false;
    }
  }, [currentFrame, data]);

  return <div ref={mountRef} className="h-full w-full" />;
}
