from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.job import JobRun, JobStatus, JobType
from app.workers.celery_app import run_security_pipeline_task

router = APIRouter()


class TriggerJobRequest(BaseModel):
    job_type: str = JobType.FULL_PIPELINE.value
    triggered_by: str = "manual"


@router.get("")
async def list_jobs(session: AsyncSession = Depends(get_db), limit: int = 50):
    result = await session.execute(select(JobRun).order_by(JobRun.created_at.desc()).limit(limit))
    return [
        {
            "id": j.id,
            "job_type": j.job_type,
            "status": j.status,
            "started_at": j.started_at,
            "completed_at": j.completed_at,
            "accounts_processed": j.accounts_processed,
            "findings_ingested": j.findings_ingested,
            "emails_sent": j.emails_sent,
            "error_message": j.error_message,
        }
        for j in result.scalars().all()
    ]


@router.post("/trigger")
async def trigger_job(payload: TriggerJobRequest, session: AsyncSession = Depends(get_db)):
    job = JobRun(job_type=payload.job_type, status=JobStatus.PENDING.value, triggered_by=payload.triggered_by)
    session.add(job)
    await session.flush()
    run_security_pipeline_task.delay(job.id, triggered_by=payload.triggered_by)
    return {"job_id": job.id, "status": "queued"}


@router.post("/{job_id}/retry")
async def retry_job(job_id: int, session: AsyncSession = Depends(get_db)):
    job = await session.get(JobRun, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    new_job = JobRun(
        job_type=job.job_type,
        status=JobStatus.PENDING.value,
        triggered_by="retry",
    )
    session.add(new_job)
    await session.flush()
    run_security_pipeline_task.delay(new_job.id, triggered_by="retry")
    return {"job_id": new_job.id, "status": "queued"}
