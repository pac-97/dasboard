from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "security_dashboard",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.scheduler_timezone,
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="run_security_pipeline", bind=True, max_retries=3)
def run_security_pipeline_task(self, job_id: int, triggered_by: str = "celery"):
    import asyncio

    from app.db.session import AsyncSessionLocal
    from app.models.job import JobRun
    from app.workers.pipeline import run_full_pipeline

    async def _run():
        async with AsyncSessionLocal() as session:
            job = await session.get(JobRun, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            await run_full_pipeline(session, job, triggered_by=triggered_by)
            await session.commit()

    try:
        asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
