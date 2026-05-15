from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.dashboard import ExecutiveOverview
from app.services.analytics.dashboard import build_executive_from_snapshot
from app.services.aws.live_data import get_live_snapshot
from app.services.analytics import inspector_analytics, cspm_analytics

router = APIRouter()


@router.get("/executive", response_model=ExecutiveOverview)
async def executive_overview(
    refresh: bool = Query(False),
    session: AsyncSession = Depends(get_db),
):
    snapshot = await get_live_snapshot(force=refresh)
    data = build_executive_from_snapshot(snapshot)
    return ExecutiveOverview(**data)


@router.get("/inspector/summary")
async def inspector_summary(refresh: bool = Query(False)):
    snapshot = await get_live_snapshot(force=refresh)
    return inspector_analytics.summary_from_findings(snapshot.get("inspector_findings", []))


@router.get("/cspm/summary")
async def cspm_summary(refresh: bool = Query(False)):
    snapshot = await get_live_snapshot(force=refresh)
    return cspm_analytics.summary_from_findings(snapshot.get("cspm_findings", []), snapshot.get("accounts", []))
