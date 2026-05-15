from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class InspectorFinding(Base):
    __tablename__ = "inspector_findings"
    __table_args__ = (
        Index("ix_inspector_account_severity", "account_id", "severity"),
        Index("ix_inspector_finding_arn", "finding_arn", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    finding_arn: Mapped[str] = mapped_column(String(512))
    account_id: Mapped[str] = mapped_column(String(12), index=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    region: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    cve_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix_available: Mapped[bool | None] = mapped_column(nullable=True)
    first_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CspmFinding(Base):
    __tablename__ = "cspm_findings"
    __table_args__ = (
        Index("ix_cspm_account_benchmark", "account_id", "benchmark"),
        Index("ix_cspm_finding_id", "finding_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    finding_id: Mapped[str] = mapped_column(String(128))
    account_id: Mapped[str] = mapped_column(String(12), index=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    benchmark: Mapped[str] = mapped_column(String(128), index=True)
    control_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_status: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    region: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    workflow_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remediation_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
