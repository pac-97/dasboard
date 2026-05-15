from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(str, Enum):
    FULL_PIPELINE = "full_pipeline"
    INGEST_INSPECTOR = "ingest_inspector"
    INGEST_CSPM = "ingest_cspm"
    INGEST_S3_COUNTS = "ingest_s3_counts"
    GENERATE_REPORTS = "generate_reports"
    SEND_EMAILS = "send_emails"
    MANUAL = "manual"


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default=JobStatus.PENDING.value)
    triggered_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    schedule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accounts_processed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    findings_ingested: Mapped[int | None] = mapped_column(Integer, nullable=True)
    emails_sent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
