"""Generate a biologically-plausible swing trajectory for unit/E2E testing.

Usage:
    python tests/fixtures/generate_synthetic.py --output tests/fixtures/swing_synthetic.mp4 --frames 120 --fps 60
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

COCO_PAIRS = [
    (5, 7), (7, 9), (6, 8), (8, 10), (5, 6),
    (5, 11), (6, 12), (11, 12), (11, 13), (13, 15),
    (12, 14), (14, 16),
]

def generate_plausible_swing(frames=120, size=(640, 480), fps=60.0):
    """Return frames and keypoint arrays for a simulated swing."""
    W, H = size
    t = np.linspace(0.0, 1.0, frames)

    # Center of the hitter around which everything pivots
    cx, cy = W // 2, H // 2 + 60

    # Swing phase functions: stance->load->stride->swing->contact->follow
    # 0-0.1: stance (hands high, narrow stance)
    # 0.1-0.2: load (hands back, shoulders rotate back, front knee flexes)
    # 0.2-0.3: stride (front ankle descends, hips open a bit)
    # 0.3-0.35: swing (rapid bat whip, hips open, contact)
    # 0.35-1.0: follow-through

    kpts_seq = np.zeros((frames, 18, 2), dtype=float)

    for i, ti in enumerate(t):
        if ti < 0.10:
            p = ti / 0.10
            # stance
            hip_y_off = 0
            sh_y_off = 0
            bat_angle = -60 - 30 * p
            stride_x = 0
            front_knee_flex = 10
            back_knee_flex = 15
            hip_rot = 0
            sh_rot = 0
        elif ti < 0.20:
            p = (ti - 0.10) / 0.10
            # load
            hip_y_off = 0
            sh_y_off = 10 * p
            bat_angle = -90 - 40 * p
            stride_x = 5 * p
            front_knee_flex = 10 + 20 * p
            back_knee_flex = 15 + 15 * p
            hip_rot = 0
            sh_rot = -15 * p
        elif ti < 0.30:
            p = (ti - 0.20) / 0.10
            # stride
            hip_y_off = -15 * p
            sh_y_off = 10 - 5 * p
            bat_angle = -130 + 20 * p
            stride_x = 5 + 25 * p
            front_knee_flex = 30 + 20 * p
            back_knee_flex = 30 - 10 * p
            hip_rot = 5 * p
            sh_rot = -15 - 10 * p
        elif ti < 0.35:
            p = (ti - 0.30) / 0.05
            # swing (explosive)
            hip_rot = 5 + 40 * p
            sh_rot = -25 + 70 * p
            hip_y_off = -15 - 5 * p
            sh_y_off = 5 + 25 * p
            bat_angle = -110 + 230 * p
            stride_x = 30
            front_knee_flex = 50 - 10 * p
            back_knee_flex = 20
        else:
            p = (ti - 0.35) / 0.65
            # follow through
            hip_rot = 45 + 5 * p
            sh_rot = 45 - 10 * p
            hip_y_off = -20 + 10 * p
            sh_y_off = 30 - 15 * p
            bat_angle = 120 - 60 * p
            stride_x = 30
            front_knee_flex = 40 + 10 * p
            back_knee_flex = 20 - 5 * p

        # Compute joint positions from angles and offsets
        spine_len = 120
        shoulder_w = 90
        upper_arm = 50
        forearm = 45
        thigh = 70
        shin = 70

        hip_c = np.array([cx, cy + hip_y_off])
        shoulder_c = np.array([cx, cy - spine_len + hip_y_off + sh_y_off])

        hip_rad = np.radians(hip_rot)
        sh_rad = np.radians(sh_rot)
        bat_rad = np.radians(bat_angle)

        kpts_seq[i, 0] = shoulder_c + np.array([0, -30])  # nose
        kpts_seq[i, 5] = shoulder_c + np.array([-shoulder_w / 2, 0])  # LS
        kpts_seq[i, 6] = shoulder_c + np.array([shoulder_w / 2, 0])  # RS

        # Arms following shoulder rotation + bat angle
        le_dir = sh_rad + np.radians(-20)
        re_dir = sh_rad + np.radians(20)
        kpts_seq[i, 7] = kpts_seq[i, 5] + upper_arm * np.array([np.cos(le_dir), np.sin(le_dir)])
        kpts_seq[i, 8] = kpts_seq[i, 6] + upper_arm * np.array([np.cos(re_dir), np.sin(re_dir)])
        kpts_seq[i, 9] = kpts_seq[i, 7] + forearm * np.array([np.cos(bat_rad - 0.2), np.sin(bat_rad - 0.2)])
        kpts_seq[i, 10] = kpts_seq[i, 8] + forearm * np.array([np.cos(bat_rad + 0.2), np.sin(bat_rad + 0.2)])

        kpts_seq[i, 11] = hip_c + np.array([-30, 0])  # LH
        kpts_seq[i, 12] = hip_c + np.array([30, 0])  # RH

        # Legs with flexion approximation
        back_thigh_ang = hip_rad - np.radians(70)
        front_thigh_ang = hip_rad + np.radians(70) - np.radians(front_knee_flex * 0.3)
        kpts_seq[i, 13] = kpts_seq[i, 11] + thigh * np.array([np.cos(back_thigh_ang), np.sin(back_thigh_ang)])
        kpts_seq[i, 14] = kpts_seq[i, 12] + thigh * np.array([np.cos(front_thigh_ang), np.sin(front_thigh_ang)])

        # Knee angles
        back_shin_ang = back_thigh_ang - np.radians(back_knee_flex)
        front_shin_ext = front_thigh_ang + np.radians(front_knee_flex * 0.2)
        kpts_seq[i, 15] = kpts_seq[i, 13] + shin * np.array([np.cos(back_shin_ang), np.sin(back_shin_ang)])
        kpts_seq[i, 16] = kpts_seq[i, 14] + shin * np.array([np.cos(front_shin_ext), np.sin(front_shin_ext)])
        kpts_seq[i, 16, 0] += stride_x

        # Draw on frame
        img = np.full((H, W, 3), 55, dtype=np.uint8)
        for a, b in COCO_PAIRS:
            pt_a = tuple(kpts_seq[i, a].astype(int))
            pt_b = tuple(kpts_seq[i, b].astype(int))
            cv2.line(img, pt_a, pt_b, (0, 240, 40), 2, lineType=cv2.LINE_AA)
        yield img


def write_video(path, frames, fps):
    frames = list(frames)
    if not frames:
        return
    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    try:
        for f in frames:
            writer.write(f)
    finally:
        writer.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("swing_synthetic.mp4"))
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--fps", type=float, default=60.0)
    args = parser.parse_args()
    frames = generate_plausible_swing(frames=args.frames, fps=args.fps)
    write_video(args.output, frames, fps=args.fps)
    print(f"Wrote {args.output}")
