from fastapi import APIRouter, Query

from app.services.aws.live_data import filter_findings_for_accounts, get_live_snapshot

router = APIRouter()


@router.get("/inspector")
async def list_inspector_findings(
    account_id: str | None = None,
    severity: str | None = None,
    region: str | None = None,
    resource_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    refresh: bool = Query(False),
):
    snapshot = await get_live_snapshot(force=refresh)
    findings = snapshot.get("inspector_findings", [])
    if account_id:
        findings = [f for f in findings if f.get("account_id") == account_id]
    if severity:
        findings = [f for f in findings if f.get("severity") == severity.upper()]
    if region:
        findings = [f for f in findings if f.get("region") == region]
    if resource_type:
        findings = [f for f in findings if f.get("resource_type") == resource_type]

    start = (page - 1) * page_size
    return findings[start : start + page_size]


@router.get("/inspector/count")
async def inspector_count(account_id: str | None = None, severity: str | None = None, refresh: bool = False):
    snapshot = await get_live_snapshot(force=refresh)
    findings = snapshot.get("inspector_findings", [])
    if account_id:
        findings = [f for f in findings if f.get("account_id") == account_id]
    if severity:
        findings = [f for f in findings if f.get("severity") == severity.upper()]
    return {"count": len(findings)}


@router.get("/cspm")
async def list_cspm_findings(
    account_id: str | None = None,
    benchmark: str | None = None,
    compliance_status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    refresh: bool = Query(False),
):
    snapshot = await get_live_snapshot(force=refresh)
    findings = snapshot.get("cspm_findings", [])
    if account_id:
        findings = [f for f in findings if f.get("account_id") == account_id]
    if benchmark:
        findings = [f for f in findings if benchmark.lower() in (f.get("benchmark") or "").lower()]
    if compliance_status:
        findings = [f for f in findings if f.get("compliance_status") == compliance_status.upper()]

    start = (page - 1) * page_size
    return findings[start : start + page_size]
