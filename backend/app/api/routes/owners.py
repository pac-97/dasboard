import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.email import EmailDeliveryLog
from app.models.owner import AccountOwner, OwnerMapping

router = APIRouter()


class OwnerCreate(BaseModel):
    name: str
    email: EmailStr
    department: str | None = None


class OwnerMappingCreate(BaseModel):
    owner_id: int
    account_id: str


@router.get("")
async def list_owners(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(AccountOwner))
    owners = result.scalars().all()
    output = []
    for owner in owners:
        mappings = await session.execute(select(OwnerMapping).where(OwnerMapping.owner_id == owner.id))
        accounts = [m.account_id for m in mappings.scalars().all()]
        output.append(
            {
                "id": owner.id,
                "name": owner.name,
                "email": owner.email,
                "department": owner.department,
                "accounts": accounts,
            }
        )
    return output


@router.post("")
async def create_owner(payload: OwnerCreate, session: AsyncSession = Depends(get_db)):
    owner = AccountOwner(name=payload.name, email=payload.email, department=payload.department)
    session.add(owner)
    await session.flush()
    return {"id": owner.id, "email": owner.email}


@router.post("/mappings")
async def create_mapping(payload: OwnerMappingCreate, session: AsyncSession = Depends(get_db)):
    existing = await session.execute(select(OwnerMapping).where(OwnerMapping.account_id == payload.account_id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Account already mapped to an owner")
    mapping = OwnerMapping(owner_id=payload.owner_id, account_id=payload.account_id)
    session.add(mapping)
    await session.flush()
    return {"id": mapping.id}


@router.post("/import")
async def bulk_import(file: UploadFile, session: AsyncSession = Depends(get_db)):
    """CSV columns: owner_name, owner_email, account_id, department (optional)"""
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    imported = 0
    for row in reader:
        email = row.get("owner_email", "").strip()
        if not email:
            continue
        result = await session.execute(select(AccountOwner).where(AccountOwner.email == email))
        owner = result.scalar_one_or_none()
        if not owner:
            owner = AccountOwner(name=row.get("owner_name", email), email=email, department=row.get("department"))
            session.add(owner)
            await session.flush()
        account_id = row.get("account_id", "").strip()
        if account_id:
            existing = await session.execute(select(OwnerMapping).where(OwnerMapping.account_id == account_id))
            if not existing.scalar_one_or_none():
                session.add(OwnerMapping(owner_id=owner.id, account_id=account_id))
                imported += 1
    return {"imported_mappings": imported}


@router.get("/{owner_id}/dashboard")
async def owner_dashboard(owner_id: int, session: AsyncSession = Depends(get_db)):
    owner = await session.get(AccountOwner, owner_id)
    if not owner:
        raise HTTPException(404, "Owner not found")
    mappings = await session.execute(select(OwnerMapping).where(OwnerMapping.owner_id == owner_id))
    account_ids = [m.account_id for m in mappings.scalars().all()]
    emails = await session.execute(
        select(EmailDeliveryLog).where(EmailDeliveryLog.owner_id == owner_id).order_by(EmailDeliveryLog.created_at.desc()).limit(20)
    )
    return {
        "owner": {"id": owner.id, "name": owner.name, "email": owner.email},
        "accounts": account_ids,
        "email_history": [
            {"subject": e.subject, "status": e.status, "sent_at": e.sent_at} for e in emails.scalars().all()
        ],
    }
