"""Generate synthetic swing test videos for CI testing.

Usage:
    python tests/fixtures/generate_dummy.py
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

# Simple "stick figure" swing pose generator
COCO_PAIRS = [
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 6),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
]


def generate_stick_swing(frames: int = 60, size: tuple[int, int] = (640, 480)):
    """Return a list of BGR frames with a simple stick figure "swinging" a bat."""
    W, H = size
    imgs = []
    for t in range(frames):
        img = np.full((H, W, 3), 32, dtype=np.uint8)
        # person center
        cx, cy = W // 2, H // 2 + 30

        # interpolate phase based on t
        p = t / (frames - 1)

        # hips (slight rotation)
        hip_angle = np.sin(p * np.pi * 2) * 15

        # shoulders (delayed rotation)
        shoulder_angle = np.sin((p - 0.1) * np.pi * 2) * 40

        # hand/bat position
        bat_angle = -90 + p * 180  # -90 (up) to 90 (down)

        # draw keypoints
        kpts = np.zeros((18, 2), dtype=int)
        kpts[0] = (cx, cy - 80)  # nose
        kpts[5] = (cx - 40 + int(np.sin(np.radians(shoulder_angle)) * 20), cy - 60)  # L shoulder
        kpts[6] = (cx + 20 + int(np.sin(np.radians(shoulder_angle)) * 20), cy - 60)  # R shoulder
        kpts[7] = (kpts[5][0] - 20, cy - 30)  # L elbow
        kpts[8] = (kpts[6][0] + 30, cy - 30)  # R elbow
        kpts[9] = (kpts[7][0] + int(np.sin(np.radians(bat_angle)) * 20), kpts[7][1] + int(np.cos(np.radians(bat_angle)) * 20))  # L wrist
        kpts[10] = (kpts[8][0] + int(np.sin(np.radians(bat_angle)) * 30), kpts[8][1] + int(np.cos(np.radians(bat_angle)) * 30))  # R wrist
        kpts[11] = (cx - 25, cy + 20 + int(np.sin(np.radians(hip_angle)) * 10))  # L hip
        kpts[12] = (cx + 25, cy + 20 + int(np.sin(np.radians(hip_angle)) * 10))  # R hip
        kpts[13] = (kpts[11][0], cy + 80)  # L knee
        kpts[14] = (kpts[12][0], cy + 80)  # R knee
        kpts[15] = (kpts[13][0], cy + 150)  # L ankle
        kpts[16] = (kpts[14][0] + int(np.sin(p * np.pi) * 30), cy + 150)  # R ankle (stride)
        kpts[17] = (cx, cy)  # neck

        for a, b in COCO_PAIRS:
            cv2.line(
                img,
                tuple(kpts[a]),
                tuple(kpts[b]),
                (0, 255, 0),
                2,
                lineType=cv2.LINE_AA,
            )
        imgs.append(img)
    return imgs


def write_video(path: Path, frames: list[np.ndarray], fps: float = 30.0):
    if not frames:
        return
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    try:
        for frm in frames:
            writer.write(frm)
    finally:
        writer.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dummy swing videos")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("swing_dummy.mp4"))
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--fps", type=float, default=30.0)
    args = parser.parse_args()

    frames = generate_stick_swing(frames=args.frames)
    write_video(args.output, frames, fps=args.fps)
    print(f"Wrote {args.output} ({args.frames} frames @ {args.fps} fps)")
