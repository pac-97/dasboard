from datetime import datetime, timezone

from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schedule import Schedule

router = APIRouter()


class ScheduleCreate(BaseModel):
    name: str
    cron_expression: str
    schedule_type: str = "custom"
    is_active: bool = True


@router.get("")
async def list_schedules(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Schedule))
    return [
        {
            "id": s.id,
            "name": s.name,
            "cron_expression": s.cron_expression,
            "schedule_type": s.schedule_type,
            "is_active": s.is_active,
            "last_run_at": s.last_run_at,
            "next_run_at": s.next_run_at,
        }
        for s in result.scalars().all()
    ]


@router.post("")
async def create_schedule(payload: ScheduleCreate, session: AsyncSession = Depends(get_db)):
    if not croniter.is_valid(payload.cron_expression):
        raise HTTPException(400, "Invalid cron expression")
    cron = croniter(payload.cron_expression, datetime.now(timezone.utc))
    schedule = Schedule(
        name=payload.name,
        cron_expression=payload.cron_expression,
        schedule_type=payload.schedule_type,
        is_active=payload.is_active,
        next_run_at=cron.get_next(datetime),
    )
    session.add(schedule)
    await session.flush()
    return {"id": schedule.id}
