import json
from datetime import datetime, timezone
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.aws.client import get_client

logger = get_logger(__name__)

BATCH_SIZE = 100


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def _list_findings_page(client, **kwargs) -> dict:
    return client.list_findings(**kwargs)


def fetch_inspector_findings(
    account_ids: list[str] | None = None,
    severities: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch organization-wide Inspector v2 findings (delegated admin). Uses EC2/instance AWS credentials."""
    settings = get_settings()
    client = get_client("inspector2", region=settings.inspector_aggregation_region, assume_role=True)
    findings: list[dict[str, Any]] = []
    filter_criteria: dict[str, Any] = {
        "findingStatus": [{"comparison": "EQUALS", "value": "ACTIVE"}],
    }

    if severities:
        filter_criteria["severity"] = [{"comparison": "EQUALS", "value": s} for s in severities]
    if account_ids:
        filter_criteria["awsAccountId"] = [{"comparison": "EQUALS", "value": a} for a in account_ids]

    next_token = None
    all_arns: list[str] = []

    while True:
        params: dict[str, Any] = {"maxResults": 100, "filterCriteria": filter_criteria}
        if next_token:
            params["nextToken"] = next_token

        response = _list_findings_page(client, **params)
        batch_arns = response.get("findings", [])
        if batch_arns:
            if isinstance(batch_arns[0], dict):
                for item in batch_arns:
                    arn = item.get("findingArn") or item.get("arn")
                    if arn:
                        all_arns.append(arn)
            else:
                all_arns.extend(batch_arns)

        next_token = response.get("nextToken")
        if not next_token:
            break

    for i in range(0, len(all_arns), BATCH_SIZE):
        chunk = all_arns[i : i + BATCH_SIZE]
        detail_response = client.batch_get_findings(findingArns=chunk)
        for f in detail_response.get("findings", []):
            findings.append(_normalize_inspector_finding(f))

    logger.info("inspector_findings_fetched", count=len(findings), arns=len(all_arns))
    return findings


def _normalize_inspector_finding(finding: dict) -> dict[str, Any]:
    resources = finding.get("resources", [{}])
    resource = resources[0] if resources else {}
    cves: list[str] = []
    if finding.get("packageVulnerabilityDetails"):
        cves = finding["packageVulnerabilityDetails"].get("vulnerabilityIds", []) or []

    return {
        "finding_arn": finding.get("findingArn", ""),
        "account_id": finding.get("awsAccountId", ""),
        "title": finding.get("title", "Untitled Finding"),
        "description": finding.get("description"),
        "severity": finding.get("severity", "INFORMATIONAL"),
        "status": finding.get("status", "ACTIVE"),
        "resource_type": resource.get("type"),
        "resource_id": resource.get("id"),
        "region": finding.get("region"),
        "cve_ids": ",".join(cves) if cves else None,
        "fix_available": finding.get("fixAvailable") == "YES",
        "first_observed_at": _parse_dt(finding.get("firstObservedAt")),
        "last_observed_at": _parse_dt(finding.get("lastObservedAt")),
        "updated_at_source": _parse_dt(finding.get("updatedAt")),
        "remediation": (finding.get("remediation", {}) or {}).get("recommendation", {}).get("text"),
        "raw_payload": json.dumps(finding, default=str),
    }


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
