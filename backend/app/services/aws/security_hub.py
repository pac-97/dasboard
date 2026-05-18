import json
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.services.aws.client import get_client

logger = get_logger(__name__)

CIS_BENCHMARK = "cis-aws-foundations-benchmark"
NIST_BENCHMARK = "nist-800-53"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def _get_findings_page(client, **kwargs) -> dict:
    return client.get_findings(**kwargs)


def _detect_benchmark(finding: dict) -> str | None:
    text = json.dumps(finding).lower()
    if CIS_BENCHMARK in text or "cis aws foundations" in text:
        return CIS_BENCHMARK
    if NIST_BENCHMARK in text or "800-53" in text:
        return NIST_BENCHMARK
    compliance = finding.get("Compliance", {}) or {}
    for req in compliance.get("RelatedRequirements", []) or []:
        rl = str(req).lower()
        if CIS_BENCHMARK in rl:
            return CIS_BENCHMARK
        if NIST_BENCHMARK in rl or "800-53" in rl:
            return NIST_BENCHMARK
    return None


def fetch_cspm_findings(account_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Fetch active Security Hub compliance findings; classify CIS / NIST in Python."""
    client = get_client("securityhub", assume_role=True)
    findings: list[dict[str, Any]] = []

    filters: dict[str, Any] = {
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
        "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}, {"Value": "NOTIFIED", "Comparison": "EQUALS"}],
    }
    if account_ids:
        filters["AwsAccountId"] = [{"Value": a, "Comparison": "EQUALS"} for a in account_ids]

    next_token = None
    while True:
        params: dict[str, Any] = {"Filters": filters, "MaxResults": 100}
        if next_token:
            params["NextToken"] = next_token
        try:
            response = _get_findings_page(client, **params)
        except Exception as exc:
            logger.warning("security_hub_fetch_error", error=str(exc))
            filters.pop("WorkflowStatus", None)
            response = _get_findings_page(client, **params)

        for f in response.get("Findings", []):
            benchmark = _detect_benchmark(f)
            if not benchmark:
                continue
            findings.append(_normalize_security_hub_finding(f, benchmark))

        next_token = response.get("NextToken")
        if not next_token:
            break

    logger.info("cspm_findings_fetched", count=len(findings))
    return findings


def _normalize_security_hub_finding(finding: dict, benchmark: str) -> dict[str, Any]:
    compliance = finding.get("Compliance", {}) or {}
    control_id = compliance.get("SecurityControlId", "")
    if not control_id and compliance.get("RelatedRequirements"):
        control_id = compliance["RelatedRequirements"][0]

    resources = finding.get("Resources", [{}])
    resource = resources[0] if resources else {}
    severity = finding.get("Severity", {})
    if isinstance(severity, dict):
        severity = severity.get("Label", "INFORMATIONAL")

    return {
        "finding_id": finding.get("Id", ""),
        "account_id": finding.get("AwsAccountId", ""),
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
