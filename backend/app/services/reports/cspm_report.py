from datetime import datetime, timezone
from pathlib import Path

import xlsxwriter

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.aws.security_hub import CIS_BENCHMARK, NIST_BENCHMARK

logger = get_logger(__name__)


def generate_cspm_report(
    findings: list[dict],
    account_id: str | None = None,
    output_path: str | None = None,
) -> str:
    settings = get_settings()
    out_dir = Path(settings.reports_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = account_id or "organization"
    filename = output_path or str(out_dir / f"cspm_report_{suffix}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.xlsx")

    workbook = xlsxwriter.Workbook(filename)
    _add_compliance_summary(workbook, findings)
    _add_cis_sheet(workbook, findings)
    _add_nist_sheet(workbook, findings)
    _add_failed_controls(workbook, findings)
    _add_service_failures(workbook, findings)
    workbook.close()

    logger.info("cspm_report_generated", path=filename, findings=len(findings))
    return filename


def _add_compliance_summary(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("Compliance Summary")
    title_fmt = workbook.add_format({"bold": True, "font_size": 16})
    header_fmt = workbook.add_format({"bold": True, "bg_color": "#1E293B", "font_color": "#F8FAFC"})

    ws.write("A1", "CSPM Compliance Report", title_fmt)
    ws.write("A2", f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    benchmarks = {CIS_BENCHMARK: "CIS AWS Foundations v5.0.0", NIST_BENCHMARK: "NIST 800-53 Rev 5"}
    row = 4
    ws.write(row, 0, "Benchmark", header_fmt)
    ws.write(row, 1, "Passed", header_fmt)
    ws.write(row, 2, "Failed", header_fmt)
    ws.write(row, 3, "Compliance %", header_fmt)
    row += 1

    for benchmark, label in benchmarks.items():
        subset = [f for f in findings if benchmark in (f.get("benchmark") or "")]
        passed = sum(1 for f in subset if f.get("compliance_status", "").upper() == "PASSED")
        failed = sum(1 for f in subset if f.get("compliance_status", "").upper() in ("FAILED", "WARNING"))
        total = passed + failed
        pct = round(passed / total * 100, 1) if total else 0
        ws.write(row, 0, label)
        ws.write(row, 1, passed)
        ws.write(row, 2, failed)
        ws.write(row, 3, f"{pct}%")
        row += 1


def _add_cis_sheet(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("CIS Controls")
    _write_controls_table(ws, workbook, [f for f in findings if CIS_BENCHMARK in (f.get("benchmark") or "")])


def _add_nist_sheet(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("NIST Controls")
    _write_controls_table(ws, workbook, [f for f in findings if NIST_BENCHMARK in (f.get("benchmark") or "")])


def _add_failed_controls(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("Failed Controls")
    failed = [f for f in findings if f.get("compliance_status", "").upper() in ("FAILED", "WARNING")]
    _write_controls_table(ws, workbook, failed)


def _add_service_failures(workbook, findings: list[dict]):
    ws = workbook.add_worksheet("Service Failures")
    services: dict[str, int] = {}
    for f in findings:
        if f.get("compliance_status", "").upper() not in ("FAILED", "WARNING"):
            continue
        svc = f.get("resource_type") or "Unknown"
        services[svc] = services.get(svc, 0) + 1

    header_fmt = workbook.add_format({"bold": True, "bg_color": "#1E293B", "font_color": "#F8FAFC"})
    ws.write(0, 0, "Service", header_fmt)
    ws.write(0, 1, "Failed Controls", header_fmt)
    for i, (svc, count) in enumerate(sorted(services.items(), key=lambda x: -x[1]), 1):
        ws.write(i, 0, svc)
        ws.write(i, 1, count)


def _write_controls_table(ws, workbook, findings: list[dict]):
    headers = ["Account", "Control", "Title", "Status", "Severity", "Resource", "Region"]
    header_fmt = workbook.add_format({"bold": True, "bg_color": "#1E293B", "font_color": "#F8FAFC", "border": 1})
    pass_fmt = workbook.add_format({"bg_color": "#DCFCE7", "border": 1})
    fail_fmt = workbook.add_format({"bg_color": "#FEE2E2", "border": 1})

    for col, h in enumerate(headers):
        ws.write(0, col, h, header_fmt)

    for row_idx, f in enumerate(findings, 1):
        status = f.get("compliance_status", "").upper()
        fmt = pass_fmt if status == "PASSED" else fail_fmt
        values = [
            f.get("account_id"),
            f.get("control_id"),
            f.get("title"),
            f.get("compliance_status"),
            f.get("severity"),
            f.get("resource_id"),
            f.get("region"),
        ]
        for col_idx, val in enumerate(values):
            ws.write(row_idx, col_idx, str(val) if val else "", fmt)

    if findings:
        ws.autofilter(0, 0, len(findings), len(headers) - 1)
