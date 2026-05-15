from fastapi import APIRouter

from app.api.routes import accounts, dashboard, email_send, findings, jobs, owners, operations, schedules

api_router = APIRouter()
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(email_send.router, prefix="/email", tags=["email"])
api_router.include_router(findings.router, prefix="/findings", tags=["findings"])
api_router.include_router(owners.router, prefix="/owners", tags=["owners"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(operations.router, prefix="/operations", tags=["operations"])
