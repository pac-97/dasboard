from datetime import datetime, timezone
from pathlib import Path

import xlsxwriter

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SEVERITY_COLORS = {
    "CRITICAL": "#DC2626",
    "HIGH": "#EA580C",
    "MEDIUM": "#CA8A04",
    "LOW": "#2563EB",
    "INFORMATIONAL": "#6B7280",
}


def generate_inspector_report(
    findings: list[dict],
    account_id: str | None = None,
    output_path: str | None = None,
) -> str:
    settings = get_settings()
    out_dir = Path(settings.reports_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = account_id or "organization"
    filename = output_path or str(out_dir / f"inspector_report_{suffix}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.xlsx")

    workbook = xlsxwriter.Workbook(filename)
    _add_summary_sheet(workbook, findings)
    _add_critical_sheet(workbook, findings)
    _add_all_findings_sheet(workbook, findings)
    _add_region_breakdown(workbook, findings)
    _add_aging_analysis(workbook, findings)
    workbook.close()

    logger.info("inspector_report_generated", path=filename, findings=len(findings))
    return filename


def _add_summary_sheet(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("Executive Summary")
    ws.set_column("A:A", 28)
    ws.set_column("B:B", 20)

    title_fmt = workbook.add_format({"bold": True, "font_size": 16, "font_color": "#0F172A"})
    header_fmt = workbook.add_format({"bold": True, "bg_color": "#1E293B", "font_color": "#F8FAFC"})
    num_fmt = workbook.add_format({"num_format": "#,##0"})

    ws.write("A1", "AWS Inspector Security Report", title_fmt)
    ws.write("A2", f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    severity_counts = _count_by_severity(findings)
    row = 4
    ws.write(row, 0, "Metric", header_fmt)
    ws.write(row, 1, "Count", header_fmt)
    row += 1
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]:
        ws.write(row, 0, sev)
        ws.write(row, 1, severity_counts.get(sev, 0), num_fmt)
        row += 1
    ws.write(row, 0, "Total Active Findings", header_fmt)
    ws.write(row, 1, len(findings), num_fmt)

    chart = workbook.add_chart({"type": "pie"})
    chart.add_series({
        "categories": ["Executive Summary", 5, 0, 5 + len(severity_counts) - 1, 0],
        "values": ["Executive Summary", 5, 1, 5 + len(severity_counts) - 1,  1],
        "name": "Severity Distribution",
    })
    chart.set_title({"name": "Findings by Severity"})
    ws.insert_chart("D4", chart, {"x_scale": 1.2, "y_scale": 1.2})


def _add_critical_sheet(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("Critical & High")
    headers = ["Account", "Severity", "Title", "Resource", "Region", "CVEs", "Fix Available", "Status"]
    _write_table(ws, workbook, [f for f in findings if f.get("severity") in ("CRITICAL", "HIGH")], headers)


def _add_all_findings_sheet(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("All Findings")
    headers = ["Account", "Severity", "Title", "Resource Type", "Resource", "Region", "CVEs", "Fix Available", "First Observed", "Status"]
    _write_table(ws, workbook, findings, headers)
    ws.autofilter(0, 0, max(len(findings), 1), len(headers) - 1)


def _add_region_breakdown(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("Region Breakdown")
    regions: dict[str, int] = {}
    for f in findings:
        r = f.get("region") or "unknown"
        regions[r] = regions.get(r, 0) + 1
    ws.write(0, 0, "Region")
    ws.write(0, 1, "Count")
    for i, (region, count) in enumerate(sorted(regions.items(), key=lambda x: -x[1]), 1):
        ws.write(i, 0, region)
        ws.write(i, 1, count)


def _add_aging_analysis(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("Aging Analysis")
    headers = ["Account", "Severity", "Title", "Days Open", "Region"]
    rows = []
    now = datetime.now(timezone.utc)
    for f in findings:
        first = f.get("first_observed_at")
        days = 0
        if first:
            if isinstance(first, str):
                first = datetime.fromisoformat(first.replace("Z", "+00:00"))
            days = (now - first).days
        rows.append({**f, "days_open": days})
    _write_table(ws, workbook, rows, headers + ["days_open"] if False else headers)


def _write_table(ws, workbook, rows: list[dict], headers: list[str]):
    header_fmt = workbook.add_format({"bold": True, "bg_color": "#1E293B", "font_color": "#F8FAFC", "border": 1})
    cell_fmt = workbook.add_format({"border": 1})
    critical_fmt = workbook.add_format({"bg_color": "#FEE2E2", "border": 1})
    high_fmt = workbook.add_format({"bg_color": "#FFEDD5", "border": 1})

    for col, h in enumerate(headers):
        ws.write(0, col, h, header_fmt)

    field_map = {
        "Account": "account_id",
        "Severity": "severity",
        "Title": "title",
        "Resource": "resource_id",
        "Resource Type": "resource_type",
        "Region": "region",
        "CVEs": "cve_ids",
        "Fix Available": "fix_available",
        "Status": "status",
        "First Observed": "first_observed_at",
        "Days Open": "days_open",
    }

    for row_idx, finding in enumerate(rows, 1):
        sev = finding.get("severity", "")
        fmt = critical_fmt if sev == "CRITICAL" else high_fmt if sev == "HIGH" else cell_fmt
        for col_idx, header in enumerate(headers):
            key = field_map.get(header, header.lower().replace(" ", "_"))
            val = finding.get(key, "")
            if isinstance(val, bool):
                val = "Yes" if val else "No"
            ws.write(row_idx, col_idx, str(val) if val is not None else "", fmt)


def _count_by_severity(findings: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "INFORMATIONAL")
        counts[sev] = counts.get(sev, 0) + 1
    return counts
