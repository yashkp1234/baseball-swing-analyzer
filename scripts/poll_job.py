import time
import sys
sys.path.insert(0, r"C:\Users\yashk\baseball_swing_analyzer")
from server.db import get_job

job_id = "8c0ab9b8-55f3-4986-8a72-9551db2d7e3d"
for i in range(60):
    j = get_job(job_id)
    status = j["status"]
    progress = j["progress"]
    step = j["current_step"]
    print(f"{i}: status={status} progress={progress} step={step}")
    if status in ("completed", "failed"):
        if status == "failed":
            print(f"ERROR: {j['error_message'][:200]}")
        break
    time.sleep(2)