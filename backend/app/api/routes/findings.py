from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.services.aws.live_data import (
    fetch_account_cspm_findings,
    fetch_account_inspector_findings,
    get_account_by_id,
    get_live_snapshot,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/accounts")
async def list_accounts(refresh: bool = Query(False)):
    """Get organization accounts list (lightweight, no findings)."""
    snapshot = await get_live_snapshot(force=refresh)
    return {
        "accounts": snapshot.get("accounts", []),
        "account_count": snapshot.get("account_count", 0),
        "fetched_at": snapshot.get("fetched_at"),
    }


@router.post("/inspector/fetch-account/{account_id}")
async def fetch_inspector_account(account_id: str):
    """Fetch Inspector findings for a specific account on-demand."""
    # Get account details from account list
    snapshot = await get_live_snapshot()
    account = get_account_by_id(snapshot.get("accounts", []), account_id)
    
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    
    # Fetch findings for this account
    result = await fetch_account_inspector_findings(account_id, account.get("account_name"))
    
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=f"Failed to fetch findings: {result.get('error')}")
    
    return {
        "account_id": result["account_id"],
        "account_name": result["account_name"],
        "findings": result["findings"],
        "stats": result["stats"],
        "fetched_at": result["fetched_at"],
    }


@router.post("/cspm/fetch-account/{account_id}")
async def fetch_cspm_account(account_id: str):
    """Fetch CSPM findings for a specific account on-demand."""
    # Get account details from account list
    snapshot = await get_live_snapshot()
    account = get_account_by_id(snapshot.get("accounts", []), account_id)
    
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    
    # Fetch findings for this account
    result = await fetch_account_cspm_findings(account_id, account.get("account_name"))
    
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=f"Failed to fetch findings: {result.get('error')}")
    
    return {
        "account_id": result["account_id"],
        "account_name": result["account_name"],
        "findings": result["findings"],
        "stats": result["stats"],
        "fetched_at": result["fetched_at"],
    }
