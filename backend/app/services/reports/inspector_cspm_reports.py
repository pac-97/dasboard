"""Generate Inspector-only XLSX report with coverage data."""

from datetime import datetime, timezone
from pathlib import Path

import xlsxwriter

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_inspector_report(account_findings: dict[str, dict], output_path: str | None = None) -> str:
    """
    Generate Inspector-only XLSX report.
    
    Args:
        account_findings: Dict mapping account_id to {
            account_name: str,
            critical: int,
            high: int,
            total: int,
            coverage: float (%)
        }
        output_path: Optional custom output path
    
    Returns:
        Path to generated XLSX file
    """
    settings = get_settings()
    out_dir = Path(settings.reports_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = output_path or str(
        out_dir / f"inspector_report_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.xlsx"
    )

    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet("Inspector Findings")
    
    # Define formats
    header_format = workbook.add_format({
        "bold": True,
        "bg_color": "#1E293B",
        "font_color": "#F8FAFC",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })
    
    data_format = workbook.add_format({
        "border": 1,
        "align": "left",
        "valign": "vcenter",
    })
    
    number_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "num_format": "0",
    })
    
    percentage_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "num_format": "0\"%\"",
    })
    
    critical_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "num_format": "0",
        "bg_color": "#7F1D1D",
        "font_color": "#FCA5A5",
    })
    
    high_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "num_format": "0",
        "bg_color": "#7C2D12",
        "font_color": "#FDBA74",
    })
    
    # Headers
    headers = ["Account Number", "Account Name", "Inspector Coverage", "Critical", "High", "All"]
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Set column widths
    worksheet.set_column(0, 0, 16)
    worksheet.set_column(1, 1, 25)
    worksheet.set_column(2, 2, 18)
    worksheet.set_column(3, 5, 12)
    
    # Data rows
    row = 1
    for account_id, data in sorted(account_findings.items()):
        worksheet.write(row, 0, account_id, data_format)
        worksheet.write(row, 1, data.get("account_name", account_id), data_format)
        worksheet.write(row, 2, data.get("coverage", 0) / 100.0, percentage_format)
        worksheet.write(row, 3, data.get("critical", 0), critical_format)
        worksheet.write(row, 4, data.get("high", 0), high_format)
        worksheet.write(row, 5, data.get("total", 0), number_format)
        row += 1
    
    workbook.close()
    logger.info("inspector_report_generated", path=filename, accounts=len(account_findings))
    return filename


def generate_cspm_report(account_scores: dict[str, dict], output_path: str | None = None) -> str:
    """
    Generate CSPM-only XLSX report from S3 scores.
    
    Args:
        account_scores: Dict mapping account_id to {
            account_name: str,
            cis_score: float,
            nist_score: float,
            cis_pass: int,
            cis_fail: int,
            nist_pass: int,
            nist_fail: int,
        }
        output_path: Optional custom output path
    
    Returns:
        Path to generated XLSX file
    """
    settings = get_settings()
    out_dir = Path(settings.reports_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = output_path or str(
        out_dir / f"cspm_report_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.xlsx"
    )

    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet("CSPM Benchmark Scores")
    
    # Define formats
    header_format = workbook.add_format({
        "bold": True,
        "bg_color": "#1E293B",
        "font_color": "#F8FAFC",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })
    
    data_format = workbook.add_format({
        "border": 1,
        "align": "left",
        "valign": "vcenter",
    })
    
    score_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "num_format": "0.0",
    })
    
    pass_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "num_format": "0",
        "bg_color": "#064E3B",
        "font_color": "#86EFAC",
    })
    
    fail_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "num_format": "0",
        "bg_color": "#7F1D1D",
        "font_color": "#FCA5A5",
    })
    
    # Headers
    headers = ["Account Number", "Account Name", "CIS Score", "CIS Pass", "CIS Fail", "NIST Score", "NIST Pass", "NIST Fail"]
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Set column widths
    worksheet.set_column(0, 0, 16)
    worksheet.set_column(1, 1, 25)
    worksheet.set_column(2, 7, 14)
    
    # Data rows
    row = 1
    for account_id, data in sorted(account_scores.items()):
        worksheet.write(row, 0, account_id, data_format)
        worksheet.write(row, 1, data.get("account_name", account_id), data_format)
        worksheet.write(row, 2, data.get("cis_score", 0), score_format)
        worksheet.write(row, 3, data.get("cis_pass", 0), pass_format)
        worksheet.write(row, 4, data.get("cis_fail", 0), fail_format)
        worksheet.write(row, 5, data.get("nist_score", 0), score_format)
        worksheet.write(row, 6, data.get("nist_pass", 0), pass_format)
        worksheet.write(row, 7, data.get("nist_fail", 0), fail_format)
        row += 1
    
    workbook.close()
    logger.info("cspm_report_generated", path=filename, accounts=len(account_scores))
    return filename
