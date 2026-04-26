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

function computeViewerBounds(data: Swing3DData) {
  const points: THREE.Vector3[] = [];
  for (const frame of data.frames) {
    for (const point of frame.keypoints) {
      if (point.length >= 3 && point.every((value) => Number.isFinite(value))) {
        points.push(new THREE.Vector3(point[0], point[1], point[2]));
      }
    }
    if (frame.bat?.handle?.length === 3 && frame.bat?.barrel?.length === 3) {
      points.push(new THREE.Vector3(frame.bat.handle[0], frame.bat.handle[1], frame.bat.handle[2]));
      points.push(new THREE.Vector3(frame.bat.barrel[0], frame.bat.barrel[1], frame.bat.barrel[2]));
    }
  }
  if (data.ball?.contact_position?.length === 3) {
    points.push(
      new THREE.Vector3(
        data.ball.contact_position[0],
        data.ball.contact_position[1],
        data.ball.contact_position[2],
      ),
    );
  }

  const fallbackCenter = new THREE.Vector3(0, 0, 0);
  if (points.length === 0) {
    return {
      center: fallbackCenter,
      size: new THREE.Vector3(2.2, 2.2, 2.2),
      radius: 1.1,
      floorY: -1,
    };
  }

  const box = new THREE.Box3().setFromPoints(points);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  return {
    center,
    size,
    radius: Math.max(sphere.radius, 0.9),
    floorY: box.min.y,
  };
}

export function SwingSkeletonViewer({ data, currentFrame, projected = false, resetToken = 0, onError }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const jointsRef = useRef<THREE.Mesh[]>([]);
  const bonesRef = useRef<THREE.Line[]>([]);
  const batRef = useRef<THREE.Mesh | null>(null);
  const ballRef = useRef<THREE.Mesh | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const defaultCameraPositionRef = useRef(new THREE.Vector3(0.8, 0.55, 2.4));
  const defaultTargetRef = useRef(new THREE.Vector3(0, 0.05, 0));

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
      const bounds = computeViewerBounds(data);
      const horizontalSpan = Math.max(bounds.size.x, bounds.size.z, 1.4);
      const verticalSpan = Math.max(bounds.size.y, 1.4);
      const cameraDistance = Math.max(bounds.radius * 2.8, horizontalSpan * 1.25, 2.1);
      const cameraTarget = bounds.center.clone();
      const cameraPosition = cameraTarget.clone().add(
        new THREE.Vector3(horizontalSpan * 0.22, verticalSpan * 0.3, cameraDistance),
      );

      const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
      camera.near = Math.max(0.01, bounds.radius / 60);
      camera.far = Math.max(50, bounds.radius * 24);
      camera.position.copy(cameraPosition);
      camera.lookAt(cameraTarget);
      cameraRef.current = camera;
      defaultCameraPositionRef.current = cameraPosition.clone();
      defaultTargetRef.current = cameraTarget.clone();

      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      rendererRef.current = renderer;
      mount.appendChild(renderer.domElement);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.minDistance = Math.max(bounds.radius * 0.9, 1.1);
      controls.maxDistance = Math.max(bounds.radius * 6, 5.2);
      controls.target.copy(cameraTarget);
      controls.update();
      controlsRef.current = controls;

      scene.add(new THREE.AmbientLight("#dbeafe", 1.2));
      const keyLight = new THREE.DirectionalLight("#ffffff", 1.15);
      keyLight.position.set(1.4, 2.2, 2.6);
      scene.add(keyLight);
      const rimLight = new THREE.DirectionalLight("#60a5fa", 0.45);
      rimLight.position.set(-2.0, 1.4, -1.2);
      scene.add(rimLight);

      const gridSize = Math.max(horizontalSpan * 2.6, 3.6);
      const grid = new THREE.GridHelper(gridSize, 12, "#143e2b", "#10202c");
      grid.position.y = bounds.floorY - 0.08;
      scene.add(grid);

      const axes = new THREE.AxesHelper(0.5);
      axes.position.set(
        cameraTarget.x - horizontalSpan * 0.55,
        bounds.floorY + 0.18,
        cameraTarget.z + horizontalSpan * 0.45,
      );
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

      const bat = new THREE.Mesh(
        new THREE.CylinderGeometry(0.018, 0.026, 1, 14),
        new THREE.MeshStandardMaterial({
          color: "#f5d36b",
          emissive: "#513809",
          roughness: 0.28,
          metalness: 0.18,
        }),
      );
      scene.add(bat);
      batRef.current = bat;

      const ball = new THREE.Mesh(
        new THREE.SphereGeometry(0.042, 16, 16),
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
  }, [data, data.keypoint_names, data.skeleton, onError, projected]);

  useEffect(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    cameraRef.current.position.copy(defaultCameraPositionRef.current);
    controlsRef.current.target.copy(defaultTargetRef.current);
    controlsRef.current.update();
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
        const handle = new THREE.Vector3(bat.handle[0], bat.handle[1], bat.handle[2]);
        const barrel = new THREE.Vector3(bat.barrel[0], bat.barrel[1], bat.barrel[2]);
        const direction = barrel.clone().sub(handle);
        const length = Math.max(direction.length(), 1e-3);
        const midpoint = handle.clone().add(barrel).multiplyScalar(0.5);

        batRef.current.visible = true;
        batRef.current.position.copy(midpoint);
        batRef.current.scale.set(1, length, 1);
        batRef.current.quaternion.setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          direction.normalize(),
        );
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
