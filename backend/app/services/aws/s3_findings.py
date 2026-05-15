import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.aws.client import get_client

logger = get_logger(__name__)


def fetch_findings_count_history(prefix: str | None = None) -> list[dict[str, Any]]:
    """Read historical findings count objects from S3."""
    settings = get_settings()
    if not settings.s3_findings_bucket:
        logger.warning("s3_findings_bucket_not_configured")
        return []

    s3 = get_client("s3")
    bucket = settings.s3_findings_bucket
    full_prefix = prefix or settings.s3_findings_prefix
    snapshots: list[dict[str, Any]] = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=full_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not (key.endswith(".json") or key.endswith(".csv")):
                continue
            body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            snapshots.extend(_parse_findings_count_object(body, key, obj.get("LastModified")))

    snapshots.sort(key=lambda x: x.get("snapshot_date") or datetime.min.replace(tzinfo=timezone.utc))
    logger.info("s3_findings_history_loaded", count=len(snapshots))
    return snapshots


def _parse_findings_count_object(body: bytes, key: str, last_modified) -> list[dict[str, Any]]:
    text = body.decode("utf-8")
    records: list[dict] = []

    if key.endswith(".json"):
        data = json.loads(text)
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = data.get("records", data.get("findings", [data]))
    elif key.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(text))
        records = list(reader)

    result = []
    for row in records:
        snapshot_date = row.get("snapshot_date") or row.get("date") or last_modified
        result.append(
            {
                "snapshot_date": _parse_date(snapshot_date),
                "account_id": row.get("account_id") or row.get("AccountId"),
                "source": row.get("source", "aggregate"),
                "critical_count": int(row.get("critical_count") or row.get("critical", 0)),
                "high_count": int(row.get("high_count") or row.get("high", 0)),
                "medium_count": int(row.get("medium_count") or row.get("medium", 0)),
                "low_count": int(row.get("low_count") or row.get("low", 0)),
                "total_count": int(row.get("total_count") or row.get("total", 0)),
                "s3_key": key,
            }
        )
    return result


def _parse_date(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if hasattr(value, "isoformat"):
        return value.replace(tzinfo=timezone.utc) if not value.tzinfo else value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
