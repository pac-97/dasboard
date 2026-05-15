from datetime import datetime

from pydantic import BaseModel, Field


class InspectorFindingOut(BaseModel):
    id: int
    finding_arn: str
    account_id: str
    account_name: str | None
    title: str
    severity: str
    status: str
    resource_type: str | None
    resource_id: str | None
    region: str | None
    cve_ids: str | None
    fix_available: bool | None
    first_observed_at: datetime | None
    last_observed_at: datetime | None

    model_config = {"from_attributes": True}


class CspmFindingOut(BaseModel):
    id: int
    finding_id: str
    account_id: str
    account_name: str | None
    benchmark: str
    control_id: str
    title: str
    compliance_status: str
    severity: str
    resource_type: str | None
    region: str | None

    model_config = {"from_attributes": True}


class FindingsFilter(BaseModel):
    account_id: str | None = None
    severity: str | None = None
    region: str | None = None
    resource_type: str | None = None
    status: str | None = None
    benchmark: str | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)
