from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.dashboard import ExecutiveOverview
from app.services.analytics.dashboard import build_executive_from_snapshot
from app.services.aws.live_data import get_live_snapshot
from app.services.analytics import inspector_analytics, cspm_analytics
from app.services.aws.s3_cspm_scores import get_cspm_scores_from_s3

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


@router.get("/cspm/scores")
async def cspm_scores(month: str | None = Query(None)):
    """
    Fetch CSPM security scores from S3 for all accounts.
    
    Returns scores for CIS AWS Foundations Benchmark v5.0.0 and NIST Special Publication 800-53 Revision 5
    Falls back to calculating scores from live findings if S3 data is unavailable.
    
    Response format:
    {
        "scores": { "account_id": { "cis_score": float, "nist_score": float, ... }, ... },
        "source": "s3" | "live_data" | "none",
        "error": str or null
    }
    """
    result = await get_cspm_scores_from_s3(month=month)
    
    # If source is "none", return structured error response
    if result.get("source") == "none":
        return {
            "scores": {},
            "source": "none",
            "error": result.get("error", "Unable to fetch CSPM scores")
        }
    
    return result
