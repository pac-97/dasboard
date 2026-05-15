from typing import Any

from app.services.aws.security_hub import CIS_BENCHMARK, NIST_BENCHMARK


def summary_from_findings(findings: list[dict], accounts: list[dict]) -> dict[str, Any]:
    cis_scores = [a.get("cis_score", 0) for a in accounts]
    nist_scores = [a.get("nist_score", 0) for a in accounts]
    cis_avg = round(sum(cis_scores) / len(cis_scores), 1) if cis_scores else 0
    nist_avg = round(sum(nist_scores) / len(nist_scores), 1) if nist_scores else 0

    services: dict[str, int] = {}
    for f in findings:
        if f.get("compliance_status") not in ("FAILED", "WARNING"):
            continue
        svc = f.get("resource_type") or "Unknown"
        services[svc] = services.get(svc, 0) + 1

    account_failed = sorted(
        [
            {
                "account_id": a["account_id"],
                "account_name": a.get("account_name", a["account_id"]),
                "failed_controls": a.get("cspm_failed_controls", 0),
            }
            for a in accounts
        ],
        key=lambda x: x["failed_controls"],
        reverse=True,
    )[:20]

    return {
        "cis_compliance": cis_avg,
        "nist_compliance": nist_avg,
        "top_failed_services": [{"service": s, "count": c} for s, c in sorted(services.items(), key=lambda x: -x[1])[:15]],
        "account_comparison": account_failed,
    }
