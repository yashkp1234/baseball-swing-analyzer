const API_BASE = "/api/jobs";

export interface CoachingLine {
  tone: "good" | "warn" | "info";
  text: string;
}

export interface AnalysisSummary {
  pose_device: string;
  source_frames: number;
  source_fps: number;
  sampled_frames: number;
  effective_analysis_fps: number;
  sampling_mode: string;
  analysis_duration_ms: number;
  pose_inference_duration_ms?: number;
}

export interface SportProfile {
  label: "baseball" | "softball" | "unknown";
  confidence: number;
  context_confidence: number;
  mechanics_confidence: number;
  reasons: string[];
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
  measurement_reliability?: "normal" | "low";
  frames: number;
  fps: number;
  phase_labels: string[];
  swing_segments?: SwingSegment[];
  primary_swing_segment?: SwingSegment | null;
  flags: {
    handedness: string;
    front_shoulder_closed_load: boolean;
    leg_action: string;
    finish_height: string;
    hip_casting: boolean;
    arm_slot_at_contact: string;
  };
}

export interface SwingSegment {
  start_frame: number;
  end_frame: number;
  contact_frame: number;
  duration_s: number;
  confidence: number;
}

export interface Frame3D {
  keypoints: number[][];
  keypoint_names: string[];
  skeleton: [number, number][];
  phase: string;
  bat?: {
    handle: number[];
    barrel: number[];
    confidence: number;
    estimate_basis: "wrist_forearm_proxy";
  };
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
  swing_segments?: SwingSegment[];
  primary_swing_segment?: SwingSegment | null;
  ball?: {
    contact_frame: number;
    contact_position: number[];
    confidence: number;
    estimate_basis: "contact_frame_barrel_proxy";
  };
  kinetic_chain_scores: { hip_to_shoulder: number; shoulder_to_hand: number; overall: number };
  energy_loss_events: EnergyLossEvent[];
  metrics: Record<string, unknown>;
  skeleton: [number, number][];
  keypoint_names: string[];
}

export interface ProjectionSummary {
  estimate_basis: string;
  exit_velocity_mph: number;
  exit_velocity_mph_low: number;
  exit_velocity_mph_high: number;
  carry_distance_ft: number;
  carry_distance_ft_low: number;
  carry_distance_ft_high: number;
  score: number;
  notes?: string[];
}

export interface ProjectionResponse {
  baseline: ProjectionSummary;
  projection: ProjectionSummary;
  viewer: Swing3DData;
  sport_profile: SportProfile | null;
  fix?: { id: string; label: string; coach_text: string } | null;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  current_step: string | null;
  progress_detail_current?: number | null;
  progress_detail_total?: number | null;
  progress_detail_label?: string | null;
  error_message: string | null;
}

export interface JobResults {
  job_id: string;
  status: "completed" | "failed";
  metrics: SwingMetrics | null;
  analysis: AnalysisSummary | null;
  sport_profile: SportProfile | null;
  coaching: CoachingLine[] | null;
  frames_3d_url: string;
  analysis_version?: string | null;
  is_current_analysis?: boolean;
}

function viewerArtifactFilename(swing?: number | null): string {
  return swing && swing > 0 ? `frames_3d_swing_${swing}.json` : "frames_3d.json";
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

export async function getFrames3D(jobId: string, swing?: number | null): Promise<Swing3DData> {
  const res = await fetch(`${API_BASE}/${jobId}/artifacts/${viewerArtifactFilename(swing)}`);
  if (!res.ok) throw new Error(`3D data failed: ${res.statusText}`);
  return res.json();
}

export async function projectSwing(
  jobId: string,
  payload: { x_factor_delta_deg?: number; head_stability_delta_norm?: number; fix_id?: string | null },
  swing?: number | null,
): Promise<ProjectionResponse> {
  const url = swing && swing > 0 ? `${API_BASE}/${jobId}/projection?swing=${swing}` : `${API_BASE}/${jobId}/projection`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Projection failed: ${res.statusText}`);
  return res.json();
}

export function artifactUrl(jobId: string, filename: string): string {
  return `${API_BASE}/${jobId}/artifacts/${filename}`;
}
