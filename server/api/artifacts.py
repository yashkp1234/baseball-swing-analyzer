"""Artifact endpoint - serve annotated video and output files."""

from pathlib import Path
import re
from typing import Iterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse

from .. import db

router = APIRouter()
_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")
_CHUNK_SIZE = 1024 * 1024


def _iter_file_range(file_path: Path, start: int, end: int) -> Iterator[bytes]:
    with file_path.open("rb") as handle:
        handle.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = handle.read(min(_CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def _invalid_range(file_size: int, detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
        detail=detail,
        headers={"Content-Range": f"bytes */{file_size}"},
    )


def _parse_byte_range(range_header: str, file_size: int) -> tuple[int, int]:
    match = _RANGE_RE.fullmatch(range_header.strip())
    if match is None:
        raise _invalid_range(file_size, "Invalid range header")

    start_text, end_text = match.groups()
    if not start_text and not end_text:
        raise _invalid_range(file_size, "Invalid range header")

    if start_text:
        start = int(start_text)
        end = int(end_text) if end_text else file_size - 1
    else:
        suffix_length = int(end_text)
        if suffix_length <= 0:
            raise _invalid_range(file_size, "Invalid range header")
        start = max(file_size - suffix_length, 0)
        end = file_size - 1

    if start >= file_size or start > end:
        raise _invalid_range(file_size, "Requested range not satisfiable")

    return start, min(end, file_size - 1)


async def build_artifact_response(
    request: Request,
    file_path: Path,
    media_type: str,
    filename: str,
):
    range_header = request.headers.get("range")
    if not range_header:
        response = FileResponse(file_path, media_type=media_type, filename=filename)
        response.headers["accept-ranges"] = "bytes"
        return response

    file_size = file_path.stat().st_size
    start, end = _parse_byte_range(range_header, file_size)
    headers = {
        "accept-ranges": "bytes",
        "content-range": f"bytes {start}-{end}/{file_size}",
        "content-length": str(end - start + 1),
        "content-disposition": f'inline; filename="{filename}"',
    }
    return StreamingResponse(
        _iter_file_range(file_path, start, end),
        media_type=media_type,
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
    )


@router.get("/{job_id}/artifacts/{filename}")
async def get_artifact(job_id: str, filename: str, request: Request):
    job = db.get_job(job_id)
    if job is None:
        return {"error": "job not found"}

    file_path = Path(job["output_dir"]) / filename
    if not file_path.exists():
        return {"error": "file not found"}

    media_types = {
        ".mp4": "video/mp4",
        ".json": "application/json",
        ".md": "text/markdown",
        ".html": "text/html",
        ".png": "image/png",
        ".jpg": "image/jpeg",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return await build_artifact_response(
        request=request,
        file_path=file_path,
        media_type=media_type,
        filename=filename,
    )
