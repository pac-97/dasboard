"""Live AWS data aggregation - On-demand per-account findings fetch."""

import asyncio
import time
from typing import Any

from app.core.logging import get_logger
from app.services.aws.inspector import fetch_inspector_findings
from app.services.aws.organizations import list_organization_accounts
from app.services.aws.security_hub import account_cspm_scores, fetch_cspm_findings

logger = get_logger(__name__)

_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}


def _aggregate_inspector(findings: list[dict]) -> dict[str, dict]:
    by_account: dict[str, dict] = {}
    for f in findings:
        aid = f.get("account_id", "")
        if not aid:
            continue
        if aid not in by_account:
            by_account[aid] = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}
        by_account[aid]["total"] += 1
        sev = (f.get("severity") or "").upper()
        if sev == "CRITICAL":
            by_account[aid]["critical"] += 1
        elif sev == "HIGH":
            by_account[aid]["high"] += 1
        elif sev == "MEDIUM":
            by_account[aid]["medium"] += 1
        elif sev == "LOW":
            by_account[aid]["low"] += 1
    return by_account


def fetch_live_snapshot(force: bool = False) -> dict[str, Any]:
    """Lightweight org snapshot - ONLY fetches account list, findings loaded on-demand."""
    global _cache
    now = time.time()
    # Cache for 1 hour
    if not force and _cache["data"] and (now - _cache["fetched_at"]) < 3600:
        logger.info("using_cached_account_list", age_seconds=now - _cache["fetched_at"])
        return _cache["data"]

    logger.info("live_aws_fetch_start_accounts_only", force=force)
    
    # ONLY fetch account list - no findings
    start = time.time()
    accounts = list_organization_accounts()
    logger.info("accounts_fetched", count=len(accounts), elapsed_seconds=time.time() - start)
    
    # Build account rows without findings (lazy-loaded on-demand)
    account_rows = []
    for acc in accounts:
        account_rows.append({
            "account_id": acc["account_id"],
            "account_name": acc.get("account_name") or acc["account_id"],
            "email": acc.get("email"),
            "inspector_status": "not_fetched",
            "inspector_findings_count": None,
            "cspm_status": "not_fetched",
            "cspm_findings_count": None,
        })
    
    payload = {
        "fetched_at": now,
        "account_count": len(account_rows),
        "accounts": account_rows,
    }
    _cache = {"data": payload, "fetched_at": now}
    
    logger.info("live_aws_fetch_done_accounts_only", accounts=len(account_rows), total_time_seconds=time.time() - start)
    return payload


async def fetch_account_inspector_findings(account_id: str, account_name: str | None = None) -> dict[str, Any]:
    """Fetch Inspector findings for specific account on-demand."""
    logger.info("account_inspector_fetch_start", account_id=account_id, account_name=account_name)
    start = time.time()
    
    try:
        # Fetch findings for this account only
        account_names = {account_id: account_name or account_id}
        
        def _fetch():
            return fetch_inspector_findings(
                account_ids=[account_id],
                account_names=account_names
            )
        
        inspector_findings = await asyncio.to_thread(_fetch)
        
        # Aggregate stats
        stats = _aggregate_inspector(inspector_findings).get(account_id, {
            "total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0
        })
        
        elapsed = time.time() - start
        logger.info("account_inspector_fetch_completed", account_id=account_id, 
                   findings_count=len(inspector_findings), elapsed_seconds=elapsed)
        
        return {
            "account_id": account_id,
            "account_name": account_name or account_id,
            "findings": inspector_findings,
            "stats": stats,
            "status": "completed",
            "fetched_at": time.time(),
        }
    except Exception as e:
        logger.error("account_inspector_fetch_failed", account_id=account_id, 
                    error=str(e), elapsed_seconds=time.time() - start)
        return {
            "account_id": account_id,
            "account_name": account_name or account_id,
            "findings": [],
            "stats": {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
            "status": "failed",
            "error": str(e),
            "fetched_at": time.time(),
        }


async def fetch_account_cspm_findings(account_id: str, account_name: str | None = None) -> dict[str, Any]:
    """Fetch CSPM findings for specific account on-demand."""
    logger.info("account_cspm_fetch_start", account_id=account_id, account_name=account_name)
    start = time.time()
    
    try:
        # Fetch findings for this account only
        account_names = {account_id: account_name or account_id}
        
        def _fetch():
            return fetch_cspm_findings(
                account_ids=[account_id],
                account_names=account_names
            )
        
        cspm_findings = await asyncio.to_thread(_fetch)
        
        # Calculate stats
        stats = account_cspm_scores(cspm_findings, account_id)
        
        elapsed = time.time() - start
        logger.info("account_cspm_fetch_completed", account_id=account_id, 
                   findings_count=len(cspm_findings), elapsed_seconds=elapsed)
        
        return {
            "account_id": account_id,
            "account_name": account_name or account_id,
            "findings": cspm_findings,
            "stats": stats,
            "status": "completed",
            "fetched_at": time.time(),
        }
    except Exception as e:
        logger.error("account_cspm_fetch_failed", account_id=account_id, 
                    error=str(e), elapsed_seconds=time.time() - start)
        return {
            "account_id": account_id,
            "account_name": account_name or account_id,
            "findings": [],
            "stats": {"cis_pass": 0, "cis_fail": 0, "nist_pass": 0, "nist_fail": 0},
            "status": "failed",
            "error": str(e),
            "fetched_at": time.time(),
        }


async def get_live_snapshot(force: bool = False) -> dict[str, Any]:
    """Get account list instantly. Findings fetched on-demand per account."""
    global _cache
    now = time.time()
    
    # Return cached account list if available
    if _cache["data"] and not force:
        cache_age = now - _cache["fetched_at"]
        logger.info("returning_cached_account_list", age_seconds=cache_age)
        return _cache["data"]
    
    # Fetch fresh account list
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(fetch_live_snapshot, force),
            timeout=30.0  # Account list fetch should be fast
        )
        logger.info("get_live_snapshot_completed")
        return result
    except asyncio.TimeoutError:
        logger.error("get_live_snapshot_timeout_30s")
        if _cache["data"]:
            return _cache["data"]
        return _empty_snapshot()
    except Exception as e:
        logger.error("get_live_snapshot_error", error=str(e), exc_type=type(e).__name__)
        if _cache["data"]:
            return _cache["data"]
        return _empty_snapshot()


def _empty_snapshot() -> dict[str, Any]:
    """Return empty account list structure."""
    return {
        "fetched_at": time.time(),
        "account_count": 0,
        "accounts": [],
    }


def get_account_by_id(accounts: list[dict], account_id: str) -> dict | None:
    """Get account details by account_id from account list."""
    for acc in accounts:
        if acc["account_id"] == account_id:
            return acc
    return None
