import json
from datetime import datetime, timezone
from typing import Any

from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.aws.client import get_client

logger = get_logger(__name__)

BATCH_SIZE = 10  # batch_get_finding_details max is 10 ARNs per call

# Transient error codes that should trigger retries
TRANSIENT_ERROR_CODES = {
    "ThrottlingException",
    "RequestLimitExceeded",
    "ServiceUnavailable",
    "InternalError",
    "InternalServerError",
    "TooManyRequestsException",
}


def _is_retryable_error(exc: Exception) -> bool:
    """Return True if error is transient and should be retried."""
    if not isinstance(exc, ClientError):
        return True  # Retry non-AWS errors (network issues, etc.)
    error_code = exc.response.get("Error", {}).get("Code", "")
    return error_code in TRANSIENT_ERROR_CODES


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30), retry=retry_if_exception(_is_retryable_error))
def _list_findings_page(client, **kwargs) -> dict:
    return client.list_findings(**kwargs)


def fetch_inspector_findings(
    account_ids: list[str] | None = None,
    severities: list[str] | None = None,
    account_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch organization-wide Inspector v2 findings (delegated admin). Uses EC2/instance AWS credentials."""
    settings = get_settings()
    account_names = account_names or {}
    logger.info("inspector_fetch_start", region=settings.inspector_aggregation_region, max_results=settings.max_inspector_results)
    
    client = get_client("inspector2", region=settings.inspector_aggregation_region, assume_role=True)
    findings: list[dict[str, Any]] = []
    filter_criteria: dict[str, Any] = {}

    if severities:
        filter_criteria["severity"] = [{"comparison": "EQUALS", "value": s} for s in severities]
    if account_ids:
        filter_criteria["awsAccountId"] = [{"comparison": "EQUALS", "value": a} for a in account_ids]

    next_token = None
    all_arns: list[str] = []
    page_count = 0
    findings_outside_region = 0

    logger.info("inspector_list_findings_start", filter_criteria=filter_criteria, target_region=settings.inspector_aggregation_region)
    while True:
        # Stop if we've reached max results
        if len(all_arns) >= settings.max_inspector_results:
            logger.info("inspector_max_results_reached", current_arns=len(all_arns), max_results=settings.max_inspector_results)
            break
            
        params: dict[str, Any] = {"maxResults": 100, "filterCriteria": filter_criteria}
        if next_token:
            params["nextToken"] = next_token

        try:
            response = _list_findings_page(client, **params)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", "")
            logger.error("inspector_list_findings_failed", error_code=error_code, error_msg=error_msg, page=page_count)
            break
        except Exception as e:
            logger.error("inspector_list_findings_unexpected_error", error=str(e), type=type(e).__name__)
            break
        batch_arns = response.get("findings", [])
        page_count += 1
        logger.info("inspector_list_findings_page", page=page_count, arns_in_page=len(batch_arns), total_arns=len(all_arns))
        
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

    logger.info("inspector_list_findings_complete", total_arns=len(all_arns), pages=page_count)
    
    # Verify ARNs are strings
    if all_arns and not isinstance(all_arns[0], str):
        logger.warning("inspector_arns_not_strings", first_arn_type=type(all_arns[0]).__name__, first_arn=str(all_arns[0])[:100])
    
    # Fetch details for each finding in batches, respecting max results limit
    arns_to_fetch = all_arns[:settings.max_inspector_results]
    total_failed_arns = 0
    for batch_idx in range(0, len(arns_to_fetch), BATCH_SIZE):
        chunk = arns_to_fetch[batch_idx : batch_idx + BATCH_SIZE]
        logger.info("inspector_batch_get_findings", batch=batch_idx // BATCH_SIZE + 1, chunk_size=len(chunk))
        try:
            detail_response = client.batch_get_finding_details(findingArns=chunk)
            # Debug: log response structure on first batch
            if batch_idx == 0:
                logger.info("inspector_batch_response_structure", 
                           response_keys=list(detail_response.keys()), 
                           findings_count=len(detail_response.get("findingDetails", [])),
                           errors_count=len(detail_response.get("errors", [])))
                # Log first finding structure if available
                if detail_response.get("findingDetails"):
                    first_finding = detail_response["findingDetails"][0]
                    logger.info("inspector_first_finding_keys", keys=list(first_finding.keys())[:15])
                    # Log a few key fields for debugging
                    logger.info("inspector_first_finding_sample",
                               finding_arn=first_finding.get("findingArn"),
                               aws_account_id=first_finding.get("awsAccountId"),
                               severity=first_finding.get("severity"),
                               status=first_finding.get("status"))
                else:
                    logger.info("inspector_batch_0_has_no_findings", response_keys=list(detail_response.keys()))
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", "")
            logger.error("inspector_batch_get_failed", error_code=error_code, error_msg=error_msg, batch=batch_idx // BATCH_SIZE + 1)
            continue
        except Exception as e:
            logger.error("inspector_batch_get_unexpected_error", error=str(e), type=type(e).__name__)
            continue
        
        findings_in_batch = len(detail_response.get("findingDetails", []))
        errors_in_batch = len(detail_response.get("errors", []))
        total_failed_arns += errors_in_batch
        logger.info("inspector_batch_findings_count", batch=batch_idx // BATCH_SIZE + 1, findings_count=findings_in_batch, errors=errors_in_batch)
        
        # Log errors if any
        if errors_in_batch > 0 and batch_idx == 0:
            logger.warning("inspector_batch_0_errors", errors=detail_response.get("errors", [])[:2])
        
        for f in detail_response.get("findingDetails", []):
            try:
                # ENFORCE: Only include findings from configured region
                finding_region = f.get("region") or settings.inspector_aggregation_region
                if finding_region != settings.inspector_aggregation_region:
                    findings_outside_region += 1
                    logger.debug("inspector_finding_outside_configured_region", 
                               finding_region=finding_region, 
                               configured_region=settings.inspector_aggregation_region,
                               finding_arn=f.get("findingArn", "")[:80])
                    continue  # Skip findings from other regions
                normalized = _normalize_inspector_finding(f, account_names)
                findings.append(normalized)
            except Exception as e:
                logger.error("inspector_finding_normalization_error", error=str(e), finding_arn=f.get("findingArn", "")[:80])
    
    logger.info("inspector_findings_fetched", count=len(findings), arns=len(all_arns), max_enforced=len(arns_to_fetch), 
               findings_outside_region_skipped=findings_outside_region, total_errors=total_failed_arns)
    return findings


def _normalize_inspector_finding(finding: dict, account_names: dict[str, str] | None = None) -> dict[str, Any]:
    account_names = account_names or {}
    resources = finding.get("resources", [{}])
    resource = resources[0] if resources else {}
    cves: list[str] = []
    if finding.get("packageVulnerabilityDetails"):
        cves = finding["packageVulnerabilityDetails"].get("vulnerabilityIds", []) or []
    
    account_id = finding.get("awsAccountId", "")
    account_name = account_names.get(account_id) or account_id

    return {
        "finding_arn": finding.get("findingArn", ""),
        "account_id": account_id,
        "account_name": account_name,
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
