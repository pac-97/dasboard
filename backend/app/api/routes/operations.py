from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.email import EmailDeliveryLog
from app.models.job import JobRun, JobStatus
from app.models.schedule import Schedule

router = APIRouter()


@router.get("/overview")
async def operations_overview(session: AsyncSession = Depends(get_db)):
    total_jobs = await session.scalar(select(func.count()).select_from(JobRun)) or 0
    failed_jobs = await session.scalar(
        select(func.count()).select_from(JobRun).where(JobRun.status == JobStatus.FAILED.value)
    ) or 0
    emails_sent = await session.scalar(
        select(func.count()).select_from(EmailDeliveryLog).where(EmailDeliveryLog.status == "sent")
    ) or 0
    emails_failed = await session.scalar(
        select(func.count()).select_from(EmailDeliveryLog).where(EmailDeliveryLog.status == "failed")
    ) or 0
    active_schedules = await session.scalar(
        select(func.count()).select_from(Schedule).where(Schedule.is_active.is_(True))
    ) or 0

    recent_jobs = await session.execute(select(JobRun).order_by(JobRun.created_at.desc()).limit(10))
    recent_emails = await session.execute(
        select(EmailDeliveryLog).order_by(EmailDeliveryLog.created_at.desc()).limit(20)
    )
    audit = await session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20))

    return {
        "stats": {
            "total_jobs": total_jobs,
            "failed_jobs": failed_jobs,
            "emails_sent": emails_sent,
            "emails_failed": emails_failed,
            "active_schedules": active_schedules,
        },
        "recent_jobs": [
            {"id": j.id, "type": j.job_type, "status": j.status, "error": j.error_message} for j in recent_jobs.scalars()
        ],
        "email_logs": [
            {"recipient": e.recipient_email, "status": e.status, "subject": e.subject} for e in recent_emails.scalars()
        ],
        "audit_history": [
            {"action": a.action, "actor": a.actor, "created_at": a.created_at} for a in audit.scalars()
        ],
    }
