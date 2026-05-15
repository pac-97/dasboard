from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.owner import AccountOwner, OwnerMapping
from app.services.aws.live_data import get_live_snapshot

router = APIRouter()


async def _attach_owners(session: AsyncSession, accounts: list[dict]) -> list[dict]:
    result = await session.execute(
        select(OwnerMapping.account_id, AccountOwner.name, AccountOwner.email, AccountOwner.id).join(
            AccountOwner, OwnerMapping.owner_id == AccountOwner.id
        )
    )
    owner_map = {
        row[0]: {"owner_id": row[3], "owner_name": row[1], "owner_email": row[2]} for row in result.all()
    }
    enriched = []
    for acc in accounts:
        row = {**acc, **owner_map.get(acc["account_id"], {})}
        enriched.append(row)
    return enriched


@router.get("/live")
async def list_accounts_live(
    refresh: bool = Query(False, description="Force refresh from AWS"),
    session: AsyncSession = Depends(get_db),
):
    snapshot = await get_live_snapshot(force=refresh)
    accounts = await _attach_owners(session, snapshot["accounts"])
    return {
        "fetched_at": snapshot["fetched_at"],
        "account_count": snapshot["account_count"],
        "org_totals": snapshot["org_totals"],
        "accounts": accounts,
    }


@router.post("/refresh")
async def refresh_accounts(session: AsyncSession = Depends(get_db)):
    snapshot = await get_live_snapshot(force=True)
    accounts = await _attach_owners(session, snapshot["accounts"])
    return {
        "status": "refreshed",
        "fetched_at": snapshot["fetched_at"],
        "account_count": len(accounts),
        "accounts": accounts,
    }
