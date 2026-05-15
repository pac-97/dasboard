from typing import Any

from app.services.aws.security_hub import CIS_BENCHMARK, NIST_BENCHMARK


def build_executive_from_snapshot(snapshot: dict) -> dict[str, Any]:
    accounts = snapshot.get("accounts", [])
    inspector_findings = snapshot.get("inspector_findings", [])

    severity: dict[str, int] = {}
    for f in inspector_findings:
        sev = f.get("severity", "INFORMATIONAL")
        severity[sev] = severity.get(sev, 0) + 1

    total = len(inspector_findings)
    critical = severity.get("CRITICAL", 0)
    high = severity.get("HIGH", 0)

    cis_scores = [a.get("cis_score", 0) for a in accounts if a.get("cis_score")]
    nist_scores = [a.get("nist_score", 0) for a in accounts if a.get("nist_score")]
    cspm_scores = [a.get("cspm_score", 0) for a in accounts if a.get("cspm_score")]

    cis_avg = round(sum(cis_scores) / len(cis_scores), 1) if cis_scores else 0
    nist_avg = round(sum(nist_scores) / len(nist_scores), 1) if nist_scores else 0
    compliance = round(sum(cspm_scores) / len(cspm_scores), 1) if cspm_scores else 0

    risky = sorted(
        [
            {
                "account_id": a["account_id"],
                "account_name": a.get("account_name", a["account_id"]),
                "total": a.get("inspector_total", 0),
                "critical": a.get("inspector_critical", 0),
                "risk_score": a.get("inspector_total", 0) * 2 + a.get("inspector_critical", 0) * 5,
            }
            for a in accounts
        ],
        key=lambda x: x["risk_score"],
        reverse=True,
    )[:10]

    services: dict[str, int] = {}
    for f in inspector_findings:
        rt = f.get("resource_type") or "Unknown"
        services[rt] = services.get(rt, 0) + 1
    top_services = sorted(services.items(), key=lambda x: -x[1])[:10]

    regions: dict[str, int] = {}
    for f in inspector_findings:
        r = f.get("region") or "unknown"
        regions[r] = regions.get(r, 0) + 1

    return {
        "total_findings": total,
        "critical_findings": critical,
        "high_findings": high,
        "medium_findings": severity.get("MEDIUM", 0),
        "low_findings": severity.get("LOW", 0),
        "compliance_score": compliance,
        "cis_score": cis_avg,
        "nist_score": nist_avg,
        "severity_distribution": severity,
        "top_risky_accounts": risky,
        "rising_risk_accounts": [],
        "most_vulnerable_services": [{"service": s, "count": c} for s, c in top_services],
        "posture_trend": [],
        "resource_exposure": regions,
        "fetched_at": snapshot.get("fetched_at"),
    }
