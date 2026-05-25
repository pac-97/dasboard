import json
from typing import Any

from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from app.core.logging import get_logger
from app.services.aws.client import get_client

logger = get_logger(__name__)

CIS_BENCHMARK = "cis-aws-foundations-benchmark"
NIST_BENCHMARK = "nist-800-53"

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
def _get_findings_page(client, **kwargs) -> dict:
    return client.get_findings(**kwargs)


def _detect_benchmark(finding: dict) -> str | None:
    """
    Detect benchmark from Security Hub finding using multiple strategies:
    
    Priority:
    1. GeneratorId (e.g., 'cis-aws-foundations-benchmark/v/5.0.0/5.3')
    2. Compliance.AssociatedStandards[].StandardsId
    3. Compliance.Standards array (legacy)
    4. Last resort: string matching in entire finding
    
    Returns: 'cis', 'nist', or None
    """
    
    # Strategy 1: Check GeneratorId
    generator_id = finding.get("GeneratorId", "") or ""
    generator_id_lower = str(generator_id).lower()
    if "cis-aws-foundations-benchmark" in generator_id_lower:
        return CIS_BENCHMARK
    if "nist" in generator_id_lower or "800-53" in generator_id_lower:
        return NIST_BENCHMARK
    
    # Strategy 2: Check Compliance.AssociatedStandards
    compliance = finding.get("Compliance", {}) or {}
    associated_standards = compliance.get("AssociatedStandards", []) or []
    for standard in associated_standards:
        standards_id = standard.get("StandardsId", "") or ""
        standards_id_lower = str(standards_id).lower()
        if "cis-aws-foundations-benchmark" in standards_id_lower:
            return CIS_BENCHMARK
        if "nist" in standards_id_lower or "800-53" in standards_id_lower:
            return NIST_BENCHMARK
    
    # Strategy 3: Check structured Standards array (legacy - kept for backward compatibility)
    standards = compliance.get("Standards", []) or []
    for standard in standards:
        standard_name = standard.get("StandardsControlArn", "") or standard.get("Name", "")
        standard_name_lower = str(standard_name).lower()
        if "cis" in standard_name_lower and "aws" in standard_name_lower:
            return CIS_BENCHMARK
        if "nist" in standard_name_lower or "800-53" in standard_name_lower:
            return NIST_BENCHMARK
    
    # Strategy 4: Fallback to structured RelatedRequirements
    for req in compliance.get("RelatedRequirements", []) or []:
        req_lower = str(req).lower()
        if "cis" in req_lower and "aws" in req_lower:
            return CIS_BENCHMARK
        if "nist" in req_lower or "800-53" in req_lower:
            return NIST_BENCHMARK
    
    # Strategy 5: Last resort: string matching in entire finding
    text = json.dumps(finding).lower()
    if "cis" in text and "aws" in text and "foundations" in text:
        return CIS_BENCHMARK
    if "nist" in text or "800-53" in text:
        return NIST_BENCHMARK
    
    return None


def fetch_cspm_findings(account_ids: list[str] | None = None, account_names: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Fetch active Security Hub compliance findings; classify CIS / NIST in Python."""
    from app.core.config import get_settings
    settings = get_settings()
    account_names = account_names or {}
    
    logger.info("cspm_fetch_start", region=settings.security_hub_region)
    client = get_client("securityhub", region=settings.security_hub_region, assume_role=True)
    findings: list[dict[str, Any]] = []

    filters: dict[str, Any] = {
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
        "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}, {"Value": "NOTIFIED", "Comparison": "EQUALS"}],
    }
    if account_ids:
        filters["AwsAccountId"] = [{"Value": a, "Comparison": "EQUALS"} for a in account_ids]

    next_token = None
    page_count = 0
    logger.info("cspm_get_findings_start", filters=str(filters))
    
    while True:
        params: dict[str, Any] = {"Filters": filters, "MaxResults": 100}
        if next_token:
            params["NextToken"] = next_token
        try:
            response = _get_findings_page(client, **params)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            error_msg = exc.response.get("Error", {}).get("Message", "")
            logger.warning("security_hub_fetch_error", error_code=error_code, error_msg=error_msg, page=page_count, retryable=_is_retryable_error(exc))
            # Create new filter dict instead of mutating - filters WorkflowStatus for retry
            filters_retry = filters.copy()
            filters_retry.pop("WorkflowStatus", None)
            params["Filters"] = filters_retry
            try:
                response = _get_findings_page(client, **params)
                logger.info("security_hub_fetch_retry_succeeded", page=page_count)
            except ClientError as retry_exc:
                retry_error_code = retry_exc.response.get("Error", {}).get("Code", "Unknown")
                logger.error("security_hub_fetch_retry_failed", error_code=retry_error_code, original_error_code=error_code)
                break  # Stop on repeated failure
            except Exception as retry_exc:
                logger.error("security_hub_fetch_retry_unexpected_error", error=str(retry_exc), type=type(retry_exc).__name__)
                break
        except Exception as exc:
            logger.error("security_hub_fetch_unexpected_error", error=str(exc), type=type(exc).__name__, page=page_count)
            break

        page_count += 1
        findings_in_page = len(response.get("Findings", []))
        logger.info("cspm_get_findings_page", page=page_count, findings_in_page=findings_in_page, total_findings=len(findings))

        for f in response.get("Findings", []):
            benchmark = _detect_benchmark(f)
            if not benchmark:
                logger.debug("cspm_finding_no_benchmark", finding_id=f.get("Id", "")[:50])
                continue
            findings.append(_normalize_security_hub_finding(f, benchmark, account_names))

        next_token = response.get("NextToken")
        if not next_token:
            break

    logger.info("cspm_findings_fetched", count=len(findings), pages=page_count, region=settings.security_hub_region)
    return findings


def _normalize_security_hub_finding(finding: dict, benchmark: str, account_names: dict[str, str] | None = None) -> dict[str, Any]:
    account_names = account_names or {}
    compliance = finding.get("Compliance", {}) or {}
    control_id = compliance.get("SecurityControlId", "")
    if not control_id and compliance.get("RelatedRequirements"):
        control_id = compliance["RelatedRequirements"][0]

    resources = finding.get("Resources", [{}])
    resource = resources[0] if resources else {}
    severity = finding.get("Severity", {})
    if isinstance(severity, dict):
        severity = severity.get("Label", "INFORMATIONAL")

    account_id = finding.get("AwsAccountId", "")
    account_name = account_names.get(account_id) or account_id

    return {
        "finding_id": finding.get("Id", ""),
        "account_id": account_id,
        "account_name": account_name,
        "benchmark": benchmark,
        "control_id": control_id,
        "title": finding.get("Title", ""),
        "description": finding.get("Description"),
        "compliance_status": (compliance.get("Status") or "FAILED").upper(),
        "severity": str(severity),
        "resource_type": resource.get("Type"),
        "resource_id": resource.get("Id"),
        "region": finding.get("Region"),
        "workflow_status": (finding.get("Workflow", {}) or {}).get("Status"),
        "remediation_url": (finding.get("Remediation", {}) or {}).get("Recommendation", {}).get("Url"),
    }


def account_cspm_scores(cspm_findings: list[dict], account_id: str) -> dict[str, float | int]:
    subset = [f for f in cspm_findings if f.get("account_id") == account_id]
    scores: dict[str, dict[str, int]] = {}

    for f in subset:
        b = f.get("benchmark", "")
        if b not in scores:
            scores[b] = {"passed": 0, "failed": 0}
        status = f.get("compliance_status", "").upper()
        if status == "PASSED":
            scores[b]["passed"] += 1
        elif status in ("FAILED", "WARNING"):
            scores[b]["failed"] += 1

    def pct(benchmark: str) -> float:
        c = scores.get(benchmark, {"passed": 0, "failed": 0})
        total = c["passed"] + c["failed"]
        return round(c["passed"] / total * 100, 1) if total else 0.0

    cis = pct(CIS_BENCHMARK)
    nist = pct(NIST_BENCHMARK)
    failed = sum(1 for f in subset if f.get("compliance_status") in ("FAILED", "WARNING"))
    overall = round((cis + nist) / 2, 1) if (cis or nist) else 0.0

    return {
        "cspm_score": overall,
        "cis_score": cis,
        "nist_score": nist,
        "cspm_total_findings": len(subset),
        "cspm_failed_controls": failed,
    }
