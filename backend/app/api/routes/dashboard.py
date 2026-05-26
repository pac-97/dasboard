import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.logging import get_logger
from app.schemas.dashboard import ExecutiveOverview
from app.services.analytics.dashboard import build_executive_from_snapshot
from app.services.aws.live_data import get_live_snapshot
from app.services.analytics import inspector_analytics, cspm_analytics
from app.services.aws.s3_cspm_scores import get_cspm_scores_from_s3

logger = get_logger(__name__)
router = APIRouter()


@router.get("/executive", response_model=ExecutiveOverview)
async def executive_overview(
    refresh: bool = Query(False),
    session: AsyncSession = Depends(get_db),
):
    snapshot = await get_live_snapshot(force=refresh)
    
    # Fetch CSPM scores from S3 with timeout and merge into accounts
    try:
        scores_result = await asyncio.wait_for(
            get_cspm_scores_from_s3(),
            timeout=15
        )
        cspm_scores = scores_result.get("scores", {})
        
        # Merge scores into accounts before building executive overview
        for account in snapshot.get("accounts", []):
            account_id = account["account_id"]
            if account_id in cspm_scores:
                scores = cspm_scores[account_id]
                account["cis_score"] = scores.get("cis_score", 0)
                account["nist_score"] = scores.get("nist_score", 0)
                # Calculate composite CSPM score (average of CIS and NIST)
                account["cspm_score"] = (scores.get("cis_score", 0) + scores.get("nist_score", 0)) / 2
    except asyncio.TimeoutError:
        logger.warning("executive_overview_cspm_scores_timeout")
    except Exception as e:
        logger.warning("executive_overview_cspm_scores_fetch_failed", error=str(e))
    
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


@router.get("/debug/s3-config")
async def debug_s3_config():
    """Debug endpoint - check S3 configuration"""
    from app.core.config import get_settings
    settings = get_settings()
    
    return {
        "cspm_scores_s3_url": settings.cspm_scores_s3_url if settings.cspm_scores_s3_url else "NOT SET",
        "s3_findings_bucket": settings.s3_findings_bucket if settings.s3_findings_bucket else "NOT SET",
        "aws_region": settings.aws_region,
    }


@router.get("/debug/s3-test")
async def debug_s3_test():
    """Debug endpoint - test S3 access with timeout"""
    import asyncio
    import boto3
    from app.core.config import get_settings
    
    settings = get_settings()
    
    try:
        # Parse S3 URL
        direct_url = settings.cspm_scores_s3_url
        if not direct_url or not direct_url.startswith("s3://"):
            return {"error": "CSPM_SCORES_S3_URL not configured or invalid", "url": direct_url}
        
        parts = direct_url.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        
        logger.info("debug_s3_test_start", bucket=bucket, key=key)
        
        # Try to fetch with timeout
        async def _fetch():
            s3 = boto3.client("s3", region_name=settings.aws_region)
            logger.info("debug_s3_test_fetching", bucket=bucket, key=key)
            response = s3.get_object(Bucket=bucket, Key=key)
            csv_content = response["Body"].read().decode("utf-8")
            return csv_content
        
        # Run with 15 second timeout
        csv_content = await asyncio.wait_for(
            asyncio.to_thread(_fetch),
            timeout=15
        )
        
        logger.info("debug_s3_test_success", size=len(csv_content))
        return {
            "success": True,
            "bucket": bucket,
            "key": key,
            "csv_size_bytes": len(csv_content),
            "first_100_chars": csv_content[:100],
        }
        
    except asyncio.TimeoutError:
        logger.error("debug_s3_test_timeout")
        return {"error": "S3 fetch timed out after 15 seconds"}
    except Exception as e:
        logger.error("debug_s3_test_error", error=str(e), error_type=type(e).__name__)
        return {"error": str(e), "error_type": type(e).__name__}


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
    try:
        # Add 20-second timeout for S3 fetch
        result = await asyncio.wait_for(
            get_cspm_scores_from_s3(month=month),
            timeout=20
        )
    except asyncio.TimeoutError:
        logger.error("cspm_scores_endpoint_timeout")
        return {
            "scores": {},
            "source": "none",
            "error": "S3 fetch timed out after 20 seconds"
        }
    except Exception as e:
        logger.error("cspm_scores_endpoint_error", error=str(e))
        return {
            "scores": {},
            "source": "none",
            "error": str(e)
        }
    
    # If source is "none", return structured error response
    if result.get("source") == "none":
        return {
            "scores": {},
            "source": "none",
            "error": result.get("error", "Unable to fetch CSPM scores")
        }
    
    return result
