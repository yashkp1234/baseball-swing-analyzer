const API_BASE = "/api/jobs";

export interface CoachingLine {
  tone: "good" | "warn" | "info";
  text: string;
}

export interface SwingMetrics {
  phase_durations: Record<string, number>;
  stride_plant_frame: number | null;
  contact_frame: number;
  hip_angle_at_contact: number;
  shoulder_angle_at_contact: number;
  x_factor_at_contact: number;
  spine_tilt_at_contact: number;
  left_knee_at_contact: number;
  right_knee_at_contact: number;
  head_displacement_total: number;
  wrist_peak_velocity_px_s: number;
  wrist_peak_velocity_normalized: number;
  pose_confidence_mean: number;
  frames: number;
  fps: number;
  phase_labels: string[];
  flags: {
    handedness: string;
    front_shoulder_closed_load: boolean;
    leg_action: string;
    finish_height: string;
    hip_casting: boolean;
    arm_slot_at_contact: string;
  };
}

export interface Frame3D {
  keypoints: number[][];
  keypoint_names: string[];
  skeleton: [number, number][];
  phase: string;
  efficiency: number;
  velocities: Record<string, number>;
  velocity_vectors?: Record<string, number[]>;
}

export interface EnergyLossEvent {
  frame: number;
  joint: string;
  joint_index: number;
  type: string;
  magnitude_pct: number;
  description: string;
}

export interface Swing3DData {
  fps: number;
  total_frames: number;
  contact_frame: number;
  stride_plant_frame: number | null;
  phase_labels: string[];
  frames: Frame3D[];
  kinetic_chain_scores: { hip_to_shoulder: number; shoulder_to_hand: number; overall: number };
  energy_loss_events: EnergyLossEvent[];
  metrics: Record<string, number | string>;
  skeleton: [number, number][];
  keypoint_names: string[];
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  current_step: string | null;
  error_message: string | null;
}

export interface JobResults {
  job_id: string;
  status: "completed" | "failed";
  metrics: SwingMetrics | null;
  coaching: CoachingLine[] | null;
  frames_3d_url: string;
}

export async function uploadVideo(file: File): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("video", file);
  const res = await fetch(`${API_BASE}/`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/${jobId}`);
  if (!res.ok) throw new Error(`Status failed: ${res.statusText}`);
  return res.json();
}

export async function getJobResults(jobId: string): Promise<JobResults> {
  const res = await fetch(`${API_BASE}/${jobId}/results`);
  if (!res.ok) throw new Error(`Results failed: ${res.statusText}`);
  return res.json();
}

export async function getFrames3D(jobId: string): Promise<Swing3DData> {
  const res = await fetch(`${API_BASE}/${jobId}/artifacts/frames_3d.json`);
  if (!res.ok) throw new Error(`3D data failed: ${res.statusText}`);
  return res.json();
}

export function artifactUrl(jobId: string, filename: string): string {
  return `${API_BASE}/${jobId}/artifacts/${filename}`;
}
