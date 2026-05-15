from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FindingsCountSnapshot(Base):
    __tablename__ = "findings_count_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    account_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PostureSnapshot(Base):
    __tablename__ = "posture_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    account_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cis_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    nist_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    inspector_critical: Mapped[int] = mapped_column(Integer, default=0)
    inspector_high: Mapped[int] = mapped_column(Integer, default=0)
    cspm_failed_controls: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
