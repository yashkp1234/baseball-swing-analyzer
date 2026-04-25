"""FastAPI app — async job queue. Upload → poll status → fetch results."""

import logging
import os
import time
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server import db
from server.api import upload, status, results, artifacts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("swingmetrics")


def _warm_models() -> None:
    t0 = time.perf_counter()
    from baseball_swing_analyzer.pose import _get_pose_model, extract_pose

    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
    _get_pose_model()
    extract_pose(dummy)
    logger.info(f"Models warmed in {time.perf_counter() - t0:.1f}s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    _warm_models()
    yield


app = FastAPI(title="SwingMetrics API", version="0.2.0", lifespan=lifespan)

_allowed_origins = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(upload.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(status.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(results.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(artifacts.router, prefix="/api/jobs", tags=["jobs"])
