from datetime import datetime, timezone
from pathlib import Path

import xlsxwriter

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.aws.live_data import get_account_by_id

logger = get_logger(__name__)


def generate_combined_account_report(
    account_ids: list[str],
    inspector_findings: list[dict],
    cspm_findings: list[dict],
    snapshot: dict,
    output_path: str | None = None,
) -> str:
    settings = get_settings()
    out_dir = Path(settings.reports_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    label = "_".join(account_ids[:3])
    if len(account_ids) > 3:
        label += f"_plus{len(account_ids) - 3}"
    filename = output_path or str(
        out_dir / f"security_report_{label}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.xlsx"
    )

    workbook = xlsxwriter.Workbook(filename)
    _summary_sheet(workbook, account_ids, inspector_findings, cspm_findings, snapshot)
    _inspector_sheet(workbook, inspector_findings)
    _cspm_sheet(workbook, cspm_findings)
    workbook.close()
    logger.info("combined_report_generated", path=filename, accounts=len(account_ids))
    return filename


def _summary_sheet(workbook, account_ids, inspector_findings, cspm_findings, snapshot):
    ws = workbook.add_worksheet("Executive Summary")
    header = workbook.add_format({"bold": True, "bg_color": "#1E293B", "font_color": "#F8FAFC"})
    ws.write(0, 0, "Account", header)
    ws.write(0, 1, "Inspector Total", header)
    ws.write(0, 2, "Critical", header)
    ws.write(0, 3, "High", header)
    ws.write(0, 4, "CSPM Score", header)
    ws.write(0, 5, "CIS %", header)
    ws.write(0, 6, "NIST %", header)

    row = 1
    for aid in account_ids:
        acc = get_account_by_id(snapshot.get("accounts", []), aid) or {}
        ws.write(row, 0, acc.get("account_name", aid))
        ws.write(row, 1, acc.get("inspector_total", 0))
        ws.write(row, 2, acc.get("inspector_critical", 0))
        ws.write(row, 3, acc.get("inspector_high", 0))
        ws.write(row, 4, f"{acc.get('cspm_score', 0)}%")
        ws.write(row, 5, f"{acc.get('cis_score', 0)}%")
        ws.write(row, 6, f"{acc.get('nist_score', 0)}%")
        row += 1

    ws.write(row + 1, 0, "Report generated")
    ws.write(row + 1, 1, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))


def _inspector_sheet(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("Inspector Findings")
    headers = ["Account", "Severity", "Title", "Resource", "Region", "CVEs", "Fix Available"]
    hfmt = workbook.add_format({"bold": True, "bg_color": "#1E293B", "font_color": "#F8FAFC"})
    for c, h in enumerate(headers):
        ws.write(0, c, h, hfmt)
    for r, f in enumerate(findings, 1):
        ws.write(r, 0, f.get("account_id", ""))
        ws.write(r, 1, f.get("severity", ""))
        ws.write(r, 2, f.get("title", ""))
        ws.write(r, 3, f.get("resource_id", ""))
        ws.write(r, 4, f.get("region", ""))
        ws.write(r, 5, f.get("cve_ids", ""))
        ws.write(r, 6, "Yes" if f.get("fix_available") else "No")
    if findings:
        ws.autofilter(0, 0, len(findings), len(headers) - 1)


def _cspm_sheet(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("CSPM Findings")
    headers = ["Account", "Benchmark", "Control", "Title", "Status", "Severity", "Region"]
    hfmt = workbook.add_format({"bold": True, "bg_color": "#1E293B", "font_color": "#F8FAFC"})
    for c, h in enumerate(headers):
        ws.write(0, c, h, hfmt)
    for r, f in enumerate(findings, 1):
        ws.write(r, 0, f.get("account_id", ""))
        ws.write(r, 1, f.get("benchmark", ""))
        ws.write(r, 2, f.get("control_id", ""))
        ws.write(r, 3, f.get("title", ""))
        ws.write(r, 4, f.get("compliance_status", ""))
        ws.write(r, 5, f.get("severity", ""))
        ws.write(r, 6, f.get("region", ""))
    if findings:
        ws.autofilter(0, 0, len(findings), len(headers) - 1)
