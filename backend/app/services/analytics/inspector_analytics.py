from typing import Any


def summary_from_findings(findings: list[dict]) -> dict[str, Any]:
    severity: dict[str, int] = {}
    regions: dict[str, int] = {}
    fix: dict[str, int] = {"true": 0, "false": 0}

    for f in findings:
        sev = f.get("severity", "INFORMATIONAL")
        severity[sev] = severity.get(sev, 0) + 1
        region = f.get("region")
        if region:
            regions[region] = regions.get(region, 0) + 1
        key = "true" if f.get("fix_available") else "false"
        fix[key] += 1

    return {
        "severity_distribution": severity,
        "region_distribution": regions,
        "fix_availability": fix,
        "total": len(findings),
    }
