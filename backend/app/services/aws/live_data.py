"""Live AWS data aggregation using the default credential chain (EC2 role / AWS CLI profile)."""

import asyncio
import time
from typing import Any

from app.core.logging import get_logger
from app.services.aws.inspector import fetch_inspector_findings
from app.services.aws.organizations import list_organization_accounts
from app.services.aws.security_hub import CIS_BENCHMARK, NIST_BENCHMARK, account_cspm_scores, fetch_cspm_findings

logger = get_logger(__name__)

_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_fetch_lock = asyncio.Lock()


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
    """Synchronous full org snapshot (run in thread pool)."""
    global _cache
    now = time.time()
    if not force and _cache["data"] and (now - _cache["fetched_at"]) < 120:
        logger.info("using_cached_snapshot", age_seconds=now - _cache["fetched_at"])
        return _cache["data"]

    logger.info("live_aws_fetch_start", force=force)
    
    # Step 1: List organization accounts
    start = time.time()
    accounts = list_organization_accounts()
    logger.info("accounts_fetched", count=len(accounts), elapsed_seconds=time.time() - start)
    
    # Step 2: Fetch Inspector findings
    start = time.time()
    inspector_findings = fetch_inspector_findings()
    logger.info("inspector_findings_fetched", count=len(inspector_findings), elapsed_seconds=time.time() - start)
    
    # Step 3: Fetch CSPM findings
    start = time.time()
    cspm_findings = fetch_cspm_findings()
    logger.info("cspm_findings_fetched", count=len(cspm_findings), elapsed_seconds=time.time() - start)
    
    # Step 4: Aggregate findings
    start = time.time()
    inspector_by_account = _aggregate_inspector(inspector_findings)
    logger.info("inspector_aggregated", accounts_with_findings=len(inspector_by_account), elapsed_seconds=time.time() - start)

    # Step 5: Build account rows
    start = time.time()
    account_rows = []
    for acc in accounts:
        aid = acc["account_id"]
        insp = inspector_by_account.get(aid, {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0})
        cspm = account_cspm_scores(cspm_findings, aid)
        account_rows.append(
            {
                "account_id": aid,
                "account_name": acc.get("account_name") or aid,
                "email": acc.get("email"),
                "inspector_total": insp["total"],
                "inspector_critical": insp["critical"],
                "inspector_high": insp["high"],
                "inspector_medium": insp["medium"],
                "inspector_low": insp["low"],
                **cspm,
            }
        )
    logger.info("account_rows_built", count=len(account_rows), elapsed_seconds=time.time() - start)

    payload = {
        "fetched_at": now,
        "account_count": len(account_rows),
        "accounts": account_rows,
        "inspector_findings": inspector_findings,
        "cspm_findings": cspm_findings,
        "org_totals": {
            "inspector_total": len(inspector_findings),
            "cspm_total": len(cspm_findings),
            "accounts": len(account_rows),
        },
    }
    _cache = {"data": payload, "fetched_at": now}
    logger.info("live_aws_fetch_done", accounts=len(account_rows), inspector=len(inspector_findings), cspm=len(cspm_findings), total_time_seconds=time.time() - now)
    return payload


async def get_live_snapshot(force: bool = False) -> dict[str, Any]:
    """Get live snapshot with background refresh strategy."""
    global _cache
    now = time.time()
    
    # Always return cached data if available (even if slightly stale) for fast UI response
    if _cache["data"] and not force:
        logger.info("returning_cached_snapshot", age_seconds=now - _cache["fetched_at"], force_refresh=force)
        # Background refresh if cache is older than 5 minutes
        if (now - _cache["fetched_at"]) > 300:
            logger.info("triggering_background_refresh")
            asyncio.create_task(_background_refresh())
        return _cache["data"]
    
    # For forced refresh or no cache, fetch synchronously with timeout
    async with _fetch_lock:
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_live_snapshot, force),
                timeout=120  # 2 minute timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.error("live_snapshot_fetch_timeout")
            # Return cached data if fetch times out
            if _cache["data"]:
                logger.info("returning_stale_cache_due_to_timeout")
                return _cache["data"]
            # Return empty structure if no cache available
            return {
                "fetched_at": now,
                "account_count": 0,
                "accounts": [],
                "inspector_findings": [],
                "cspm_findings": [],
                "org_totals": {
                    "inspector_total": 0,
                    "cspm_total": 0,
                    "accounts": 0,
                },
            }


async def _background_refresh():
    """Background task to refresh cache without blocking UI."""
    try:
        async with _fetch_lock:
            await asyncio.to_thread(fetch_live_snapshot, False)
    except Exception as e:
        logger.error("background_refresh_error", error=str(e))


def filter_findings_for_accounts(snapshot: dict, account_ids: list[str]) -> tuple[list[dict], list[dict]]:
    ids = set(account_ids)
    inspector = [f for f in snapshot.get("inspector_findings", []) if f.get("account_id") in ids]
    cspm = [f for f in snapshot.get("cspm_findings", []) if f.get("account_id") in ids]
    return inspector, cspm


def get_account_row(snapshot: dict, account_id: str) -> dict | None:
    for row in snapshot.get("accounts", []):
        if row["account_id"] == account_id:
            return row
    return None
