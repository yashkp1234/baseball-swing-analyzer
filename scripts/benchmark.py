import time, sys, json
sys.path.insert(0, r"C:\Users\yashk\baseball_swing_analyzer")

t0 = time.time()
from baseball_swing_analyzer.analyzer import analyze_swing
print(f"Import: {time.time()-t0:.1f}s")

from pathlib import Path
video = Path(r"C:\Users\yashk\baseball_swing_analyzer\data\videos\test_swing_2_random_stuff_happening.mp4")
out = Path(r"C:\Users\yashk\baseball_swing_analyzer\outputs\benchmark_test")
out.mkdir(parents=True, exist_ok=True)

t1 = time.time()
result = analyze_swing(video, output_dir=out, annotate=True, handedness="auto")
t2 = time.time()
print(f"Total analysis: {t2-t1:.1f}s")
print(f"Frames processed: {result.get('frames')}")
print(f"Contact frame: {result.get('contact_frame')}")

# Now benchmark individual stages
print("\n--- Stage-by-stage benchmark ---")
from baseball_swing_analyzer.detection import detect_person, reset_tracker
from baseball_swing_analyzer.ingestion import get_video_properties, load_video
from baseball_swing_analyzer.pose import extract_pose
from baseball_swing_analyzer.phases import classify_phases
from baseball_swing_analyzer.metrics import wrist_velocity
from baseball_swing_analyzer.reporter import build_report
from baseball_swing_analyzer.visualizer import annotate_frame
import cv2
import numpy as np

TARGET_FPS = 15.0

props = get_video_properties(video)
total_frames = props.total_frames
fps = props.fps
step = max(1, round(fps / TARGET_FPS))
indices = list(range(0, total_frames, step))
print(f"Source: {total_frames} frames @ {fps:.1f}fps, processing {len(indices)} frames")

# Stage 1: Person detection
t_det_start = time.time()
cap = cv2.VideoCapture(str(video))
det_count = 0
for frame_idx in range(total_frames):
    ret, frame = cap.read()
    if not ret:
        break
    if frame_idx in indices:
        bbox = detect_person(frame)
        det_count += 1
        if det_count % 50 == 0:
            print(f"  Detection: {det_count}/{len(indices)}")
cap.release()
t_det_end = time.time()
print(f"Detection+pose: {t_det_end - t_det_start:.1f}s for {det_count} frames")
print(f"Per-frame: {(t_det_end - t_det_start) / det_count * 1000:.0f}ms")

# Check output files
for f in out.iterdir():
    print(f"Output: {f.name} ({f.stat().st_size:,} bytes)")