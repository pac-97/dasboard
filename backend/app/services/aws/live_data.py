"""Live AWS data aggregation using the default credential chain (EC2 role / AWS CLI profile)."""

import asyncio
import time
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.finding import CspmFinding, InspectorFinding
from app.services.aws.inspector import fetch_inspector_findings
from app.services.aws.organizations import list_organization_accounts
from app.services.aws.security_hub import CIS_BENCHMARK, NIST_BENCHMARK, account_cspm_scores, fetch_cspm_findings

logger = get_logger(__name__)

_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_fetch_lock = asyncio.Lock()


async def _persist_findings_to_db(inspector_findings: list[dict], cspm_findings: list[dict]) -> None:
    """Persist findings to database asynchronously."""
    try:
        async with AsyncSessionLocal() as session:
            # Delete old findings to maintain fresh data
            await session.execute(delete(InspectorFinding))
            await session.execute(delete(CspmFinding))
            
            # Persist Inspector findings
            for finding in inspector_findings:
                db_finding = InspectorFinding(
                    finding_arn=finding.get("finding_arn", ""),
                    account_id=finding.get("account_id", ""),
                    account_name=finding.get("account_name"),
                    title=finding.get("title", ""),
                    description=finding.get("description"),
                    severity=finding.get("severity", "INFORMATIONAL"),
                    status=finding.get("status", "ACTIVE"),
                    resource_type=finding.get("resource_type"),
                    resource_id=finding.get("resource_id"),
                    region=finding.get("region"),
                    cve_ids=finding.get("cve_ids"),
                    fix_available=finding.get("fix_available"),
                    first_observed_at=finding.get("first_observed_at"),
                    last_observed_at=finding.get("last_observed_at"),
                    updated_at_source=finding.get("updated_at_source"),
                    remediation=finding.get("remediation"),
                    raw_payload=finding.get("raw_payload"),
                )
                session.add(db_finding)
            
            # Persist CSPM findings
            for finding in cspm_findings:
                db_finding = CspmFinding(
                    finding_id=finding.get("finding_id", ""),
                    account_id=finding.get("account_id", ""),
                    account_name=finding.get("account_name"),
                    benchmark=finding.get("benchmark", ""),
                    control_id=finding.get("control_id", ""),
                    title=finding.get("title", ""),
                    description=finding.get("description"),
                    compliance_status=finding.get("compliance_status", "FAILED"),
                    severity=finding.get("severity", "INFORMATIONAL"),
                    resource_type=finding.get("resource_type"),
                    resource_id=finding.get("resource_id"),
                    region=finding.get("region"),
                    workflow_status=finding.get("workflow_status"),
                    remediation_url=finding.get("remediation_url"),
                )
                session.add(db_finding)
            
            await session.commit()
            logger.info("findings_persisted_to_db", inspector_count=len(inspector_findings), cspm_count=len(cspm_findings))
    except Exception as e:
        logger.error("db_persistence_error", error=str(e), exc_type=type(e).__name__)


async def _load_findings_from_db() -> tuple[list[dict], list[dict]]:
    """Load findings from database for cold-start or cache failure recovery."""
    try:
        async with AsyncSessionLocal() as session:
            inspector_rows = await session.execute(select(InspectorFinding))
            cspm_rows = await session.execute(select(CspmFinding))
            
            inspector_findings = [
                {
                    "finding_arn": f.finding_arn,
                    "account_id": f.account_id,
                    "account_name": f.account_name,
                    "title": f.title,
                    "description": f.description,
                    "severity": f.severity,
                    "status": f.status,
                    "resource_type": f.resource_type,
                    "resource_id": f.resource_id,
                    "region": f.region,
                    "cve_ids": f.cve_ids,
                    "fix_available": f.fix_available,
                    "first_observed_at": f.first_observed_at,
                    "last_observed_at": f.last_observed_at,
                    "updated_at_source": f.updated_at_source,
                    "remediation": f.remediation,
                    "raw_payload": f.raw_payload,
                }
                for f in inspector_rows.scalars()
            ]
            
            cspm_findings = [
                {
                    "finding_id": f.finding_id,
                    "account_id": f.account_id,
                    "account_name": f.account_name,
                    "benchmark": f.benchmark,
                    "control_id": f.control_id,
                    "title": f.title,
                    "description": f.description,
                    "compliance_status": f.compliance_status,
                    "severity": f.severity,
                    "resource_type": f.resource_type,
                    "resource_id": f.resource_id,
                    "region": f.region,
                    "workflow_status": f.workflow_status,
                    "remediation_url": f.remediation_url,
                }
                for f in cspm_rows.scalars()
            ]
            
            logger.info("findings_loaded_from_db", inspector_count=len(inspector_findings), cspm_count=len(cspm_findings))
            return inspector_findings, cspm_findings
    except Exception as e:
        logger.error("db_load_error", error=str(e), exc_type=type(e).__name__)
        return [], []


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
    """Synchronous full org snapshot (run in thread pool). Persists to database for durability."""
    global _cache
    now = time.time()
    # Use longer TTL (3600s) since we now have database backup
    if not force and _cache["data"] and (now - _cache["fetched_at"]) < 3600:
        logger.info("using_cached_snapshot", age_seconds=now - _cache["fetched_at"])
        return _cache["data"]

    logger.info("live_aws_fetch_start", force=force)
    
    # Step 1: List organization accounts
    start = time.time()
    accounts = list_organization_accounts()
    logger.info("accounts_fetched", count=len(accounts), elapsed_seconds=time.time() - start)
    
    # Create account name lookup for enrichment
    account_names = {a["account_id"]: a.get("account_name") for a in accounts}
    
    # Step 2: Fetch Inspector findings
    start = time.time()
    inspector_findings = fetch_inspector_findings(account_names=account_names)
    logger.info("inspector_findings_fetched", count=len(inspector_findings), elapsed_seconds=time.time() - start)
    
    # Step 3: Fetch CSPM findings
    start = time.time()
    cspm_findings = fetch_cspm_findings(account_names=account_names)
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
    
    # Persist findings to database for durability (non-blocking, failures logged)
    try:
        asyncio.run(_persist_findings_to_db(inspector_findings, cspm_findings))
    except Exception as e:
        logger.warning("db_persistence_skipped", error=str(e))
    
    logger.info("live_aws_fetch_done", accounts=len(account_rows), inspector=len(inspector_findings), cspm=len(cspm_findings), total_time_seconds=time.time() - now)
    return payload


async def get_live_snapshot(force: bool = False) -> dict[str, Any]:
    """Get live snapshot - returns cached data immediately, refreshes in background, falls back to database."""
    global _cache
    now = time.time()
    
    # Always return cached data if available for instant UI response
    if _cache["data"] and not force:
        cache_age = now - _cache["fetched_at"]
        logger.info("returning_cached_snapshot", age_seconds=cache_age, force_refresh=force)
        return _cache["data"]
    
    # For forced refresh or no cache, fetch with timeout
    async with _fetch_lock:
        try:
            # Use asyncio.wait_for with a reasonable timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(fetch_live_snapshot, force),
                timeout=120.0
            )
            logger.info("fetch_completed_successfully")
            return result
        except asyncio.TimeoutError:
            logger.error("live_snapshot_fetch_timeout_2min")
            # Try cached data first, then database
            if _cache["data"]:
                logger.info("returning_stale_cache_after_timeout")
                return _cache["data"]
            # Try loading from database
            inspector_findings, cspm_findings = await _load_findings_from_db()
            if inspector_findings or cspm_findings:
                logger.info("returning_data_from_database_after_timeout")
                return {
                    "fetched_at": now,
                    "account_count": 0,
                    "accounts": [],
                    "inspector_findings": inspector_findings,
                    "cspm_findings": cspm_findings,
                    "org_totals": {
                        "inspector_total": len(inspector_findings),
                        "cspm_total": len(cspm_findings),
                        "accounts": 0,
                    },
                }
            # Return empty structure if no data available
            return _empty_snapshot()
        except Exception as e:
            logger.error("live_snapshot_fetch_error", error=str(e), exc_type=type(e).__name__)
            # Try cached data first
            if _cache["data"]:
                logger.info("returning_cached_data_after_error")
                return _cache["data"]
            # Try loading from database
            inspector_findings, cspm_findings = await _load_findings_from_db()
            if inspector_findings or cspm_findings:
                logger.info("returning_data_from_database_after_error")
                return {
                    "fetched_at": now,
                    "account_count": 0,
                    "accounts": [],
                    "inspector_findings": inspector_findings,
                    "cspm_findings": cspm_findings,
                    "org_totals": {
                        "inspector_total": len(inspector_findings),
                        "cspm_total": len(cspm_findings),
                        "accounts": 0,
                    },
                }
            return _empty_snapshot()


def _empty_snapshot() -> dict[str, Any]:
    """Return empty snapshot structure."""
    return {
        "fetched_at": time.time(),
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
