"""FastAPI application — SwingMetrics API server."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .api import upload, status, results, artifacts


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    Path("uploads").mkdir(exist_ok=True)
    Path("outputs").mkdir(exist_ok=True)
    yield


app = FastAPI(title="SwingMetrics API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(status.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(results.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(artifacts.router, prefix="/api/jobs", tags=["artifacts"])


@app.get("/api/jobs")
async def list_jobs():
    return db.list_jobs()