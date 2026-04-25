export interface Frame3D {
  keypoints: number[][];
  keypoint_names: string[];
  skeleton: [number, number][];
  phase: string;
  efficiency: number;
  velocities: Record<string, number>;
  velocity_vectors?: Record<string, number[]>;
}

export interface Swing3DData {
  fps: number;
  total_frames: number;
  contact_frame: number;
  stride_plant_frame: number | null;
  phase_labels: string[];
  frames: Frame3D[];
  kinetic_chain_scores: {
    hip_to_shoulder: number;
    shoulder_to_hand: number;
    overall: number;
  };
  energy_loss_events: {
    frame: number;
    joint: string;
    type: string;
    magnitude_pct: number;
    description: string;
  }[];
  metrics: Record<string, number | string>;
  skeleton: [number, number][];
  keypoint_names: string[];
}