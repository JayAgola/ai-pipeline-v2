"""
VideoAgent FastAPI endpoint with async job queue.
POST /render-video → returns job_id immediately
GET /job/{job_id}/status → returns status + download URL when done
"""
import os
import uuid
import subprocess
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from supabase import create_client

router = APIRouter()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# In-memory job store — replace with Redis for production
jobs = {}

class VideoRequest(BaseModel):
    topic: str
    title: str
    script: str
    audio_url: str
    points: list[str]
    channel_name: str = "Zynto AI"

class JobStatus(BaseModel):
    job_id: str
    status: str  # queued | processing | done | failed
    video_url: str | None = None
    error: str | None = None
    created_at: str
    completed_at: str | None = None

def render_video_task(job_id: str, request: VideoRequest):
    """Background task — runs Remotion render and uploads to Supabase."""
    try:
        jobs[job_id]["status"] = "processing"
        output_path = Path(f"output/video_{job_id}.mp4")
        output_path.parent.mkdir(exist_ok=True)

        # Trigger Remotion render
        result = subprocess.run([
            "npx", "remotion", "render",
            "src/index.ts",
            "AIVideoTemplate",
            str(output_path),
            f"--props={{\"title\":\"{request.title}\",\"points\":{request.points}}}"
        ], capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            raise Exception(f"Render failed: {result.stderr}")

        # Upload to Supabase Storage
        with open(output_path, "rb") as f:
            file_bytes = f.read()

        storage_path = f"videos/{job_id}.mp4"
        supabase.storage.from_("pipeline-outputs").upload(
            storage_path,
            file_bytes,
            {"content-type": "video/mp4"}
        )

        video_url = supabase.storage.from_(
            "pipeline-outputs"
        ).get_public_url(storage_path)

        # Save to DB
        supabase.table("pipeline_jobs").update({
            "status": "done",
            "video_url": video_url,
            "completed_at": datetime.now().isoformat()
        }).eq("job_id", job_id).execute()

        jobs[job_id]["status"] = "done"
        jobs[job_id]["video_url"] = video_url
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

        # Clean up local file
        output_path.unlink(missing_ok=True)

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        supabase.table("pipeline_jobs").update({
            "status": "failed",
            "error": str(e)
        }).eq("job_id", job_id).execute()


@router.post("/render-video", response_model=JobStatus)
async def render_video(
    request: VideoRequest,
    background_tasks: BackgroundTasks
):
    """Start async video render. Returns job_id immediately."""
    job_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    job = {
        "job_id": job_id,
        "status": "queued",
        "video_url": None,
        "error": None,
        "created_at": created_at,
        "completed_at": None
    }
    jobs[job_id] = job

    # Save to Supabase
    supabase.table("pipeline_jobs").insert({
        "job_id": job_id,
        "topic": request.topic,
        "title": request.title,
        "status": "queued",
        "created_at": created_at
    }).execute()

    # Start background render
    background_tasks.add_task(render_video_task, job_id, request)

    return JobStatus(**job)


@router.get("/job/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Poll this endpoint to check render progress."""
    if job_id not in jobs:
        # Try DB fallback
        result = supabase.table("pipeline_jobs")\
            .select("*").eq("job_id", job_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobStatus(**result.data[0])
    return JobStatus(**jobs[job_id])