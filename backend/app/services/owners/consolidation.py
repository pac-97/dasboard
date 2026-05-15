from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.owner import AccountOwner, OwnerMapping

logger = get_logger(__name__)

UNASSIGNED_OWNER_EMAIL = "__unassigned__"


async def load_owner_account_map(session: AsyncSession) -> dict[str, dict]:
    """Map account_id -> owner details. One owner may own multiple accounts."""
    result = await session.execute(
        select(OwnerMapping.account_id, AccountOwner.id, AccountOwner.name, AccountOwner.email).join(
            AccountOwner, OwnerMapping.owner_id == AccountOwner.id
        )
    )
    mapping: dict[str, dict] = {}
    for account_id, owner_id, name, email in result.all():
        mapping[account_id] = {"owner_id": owner_id, "owner_name": name, "owner_email": email}
    return mapping


def consolidate_by_owner(
    account_summaries: list[dict],
    owner_map: dict[str, dict],
) -> dict[str, dict[str, Any]]:
    """
    Consolidate account-level summaries into one entry per owner email.
    Ensures a single email per owner with all owned accounts included.
    """
    by_owner: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "owner_name": "Unassigned",
            "owner_email": UNASSIGNED_OWNER_EMAIL,
            "owner_id": None,
            "accounts": [],
            "inspector_summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0},
            "cspm_summary": {"cis_score": 0, "nist_score": 0, "failed_controls": 0},
        }
    )

    for summary in account_summaries:
        account_id = summary.get("account_id", "")
        owner = owner_map.get(account_id)
        if owner:
            key = owner["owner_email"]
            by_owner[key]["owner_name"] = owner["owner_name"]
            by_owner[key]["owner_email"] = owner["owner_email"]
            by_owner[key]["owner_id"] = owner["owner_id"]
        else:
            key = UNASSIGNED_OWNER_EMAIL
            by_owner[key]["owner_name"] = "Unassigned Accounts"

        entry = by_owner[key]
        entry["accounts"].append(summary)

        insp = entry["inspector_summary"]
        insp["critical"] += summary.get("critical", 0)
        insp["high"] += summary.get("high", 0)
        insp["medium"] += summary.get("medium", 0)
        insp["low"] += summary.get("low", 0)
        insp["total"] += summary.get("total", 0)

        cspm = entry["cspm_summary"]
        if summary.get("cis_score") is not None:
            scores = [a.get("cis_score", 0) for a in entry["accounts"] if a.get("cis_score") is not None]
            cspm["cis_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        if summary.get("nist_score") is not None:
            scores = [a.get("nist_score", 0) for a in entry["accounts"] if a.get("nist_score") is not None]
            cspm["nist_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        cspm["failed_controls"] += summary.get("failed_controls", 0)

    logger.info("owners_consolidated", owner_count=len(by_owner))
    return dict(by_owner)
