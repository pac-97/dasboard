"""Generate Inspector-only XLSX report with coverage data."""

from datetime import datetime, timezone
from pathlib import Path

import xlsxwriter

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_inspector_report(account_findings: dict[str, dict], findings_data: list[dict] | None = None, output_path: str | None = None) -> str:
    """
    Generate Inspector-only XLSX report with summary and detailed findings.
    
    Args:
        account_findings: Dict mapping account_id to {
            account_name: str,
            critical: int,
            high: int,
            total: int,
            coverage: float (%)
        }
        findings_data: List of detailed finding dictionaries (optional)
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
    
    # Summary worksheet
    summary_sheet = workbook.add_worksheet("Summary")
    
    # Detailed findings worksheet if data provided
    if findings_data:
        findings_sheet = workbook.add_worksheet("All Findings")
    
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
    
    # ===== SUMMARY SHEET =====
    # Headers for summary
    headers = ["Account Number", "Account Name", "Inspector Coverage", "Critical", "High", "All"]
    for col, header in enumerate(headers):
        summary_sheet.write(0, col, header, header_format)
    
    # Set column widths for summary
    summary_sheet.set_column(0, 0, 16)
    summary_sheet.set_column(1, 1, 25)
    summary_sheet.set_column(2, 2, 18)
    summary_sheet.set_column(3, 5, 12)
    
    # Data rows for summary
    row = 1
    for account_id, data in sorted(account_findings.items()):
        summary_sheet.write(row, 0, account_id, data_format)
        summary_sheet.write(row, 1, data.get("account_name", account_id), data_format)
        summary_sheet.write(row, 2, data.get("coverage", 0) / 100.0, percentage_format)
        summary_sheet.write(row, 3, data.get("critical", 0), critical_format)
        summary_sheet.write(row, 4, data.get("high", 0), high_format)
        summary_sheet.write(row, 5, data.get("total", 0), number_format)
        row += 1
    
    # ===== DETAILED FINDINGS SHEET =====
    if findings_data:
        # Format for severity columns
        severity_critical = workbook.add_format({
            "border": 1,
            "align": "left",
            "bg_color": "#7F1D1D",
            "font_color": "#FCA5A5",
            "text_wrap": True,
        })
        
        severity_high = workbook.add_format({
            "border": 1,
            "align": "left",
            "bg_color": "#7C2D12",
            "font_color": "#FDBA74",
            "text_wrap": True,
        })
        
        severity_medium = workbook.add_format({
            "border": 1,
            "align": "left",
            "bg_color": "#854D0E",
            "font_color": "#FED7AA",
            "text_wrap": True,
        })
        
        text_format = workbook.add_format({
            "border": 1,
            "align": "left",
            "valign": "top",
            "text_wrap": True,
        })
        
        # Headers for detailed findings
        finding_headers = [
            "Account Number",
            "Account Name", 
            "Severity",
            "Title",
            "Description",
            "Resource Type",
            "Resource ID",
            "Region",
            "CVE IDs",
            "Fix Available",
            "First Observed",
            "Last Observed",
            "Remediation"
        ]
        for col, header in enumerate(finding_headers):
            findings_sheet.write(0, col, header, header_format)
        
        # Set column widths for findings
        findings_sheet.set_column(0, 0, 16)  # Account Number
        findings_sheet.set_column(1, 1, 25)  # Account Name
        findings_sheet.set_column(2, 2, 12)  # Severity
        findings_sheet.set_column(3, 3, 30)  # Title
        findings_sheet.set_column(4, 4, 40)  # Description
        findings_sheet.set_column(5, 5, 18)  # Resource Type
        findings_sheet.set_column(6, 6, 30)  # Resource ID
        findings_sheet.set_column(7, 7, 12)  # Region
        findings_sheet.set_column(8, 8, 20)  # CVE IDs
        findings_sheet.set_column(9, 9, 12)  # Fix Available
        findings_sheet.set_column(10, 10, 18)  # First Observed
        findings_sheet.set_column(11, 11, 18)  # Last Observed
        findings_sheet.set_column(12, 12, 35)  # Remediation
        
        # Write findings data
        f_row = 1
        for finding in sorted(findings_data, key=lambda x: (x.get("account_id", ""), x.get("severity", ""), -x.get("created_at", 0))):
            severity = finding.get("severity", "LOW").upper()
            
            # Choose format based on severity
            if severity == "CRITICAL":
                sev_format = severity_critical
            elif severity == "HIGH":
                sev_format = severity_high
            elif severity == "MEDIUM":
                sev_format = severity_medium
            else:
                sev_format = text_format
            
            findings_sheet.write(f_row, 0, finding.get("account_id", ""), data_format)
            findings_sheet.write(f_row, 1, finding.get("account_name", ""), data_format)
            findings_sheet.write(f_row, 2, severity, sev_format)
            findings_sheet.write(f_row, 3, finding.get("title", ""), text_format)
            findings_sheet.write(f_row, 4, finding.get("description", ""), text_format)
            findings_sheet.write(f_row, 5, finding.get("resource_type", ""), data_format)
            findings_sheet.write(f_row, 6, finding.get("resource_id", ""), data_format)
            findings_sheet.write(f_row, 7, finding.get("region", ""), data_format)
            findings_sheet.write(f_row, 8, finding.get("cve_ids", ""), data_format)
            findings_sheet.write(f_row, 9, "Yes" if finding.get("fix_available") else "No", data_format)
            
            # Format dates
            first_obs = finding.get("first_observed_at")
            if first_obs:
                findings_sheet.write(f_row, 10, str(first_obs)[:16], data_format)
            else:
                findings_sheet.write(f_row, 10, "", data_format)
            
            last_obs = finding.get("last_observed_at")
            if last_obs:
                findings_sheet.write(f_row, 11, str(last_obs)[:16], data_format)
            else:
                findings_sheet.write(f_row, 11, "", data_format)
            
            findings_sheet.write(f_row, 12, finding.get("remediation", ""), text_format)
            f_row += 1
    
    workbook.close()
    logger.info("inspector_report_generated", path=filename, accounts=len(account_findings))
    return filename


def generate_cspm_report(account_scores: dict[str, dict], findings_data: list[dict] | None = None, output_path: str | None = None) -> str:
    """
    Generate multi-sheet CSPM XLSX report with executive summary and filtered findings by severity.
    
    Creates 5 sheets:
    - Executive Summary: Account metrics and finding breakdown
    - All Failed Findings: All FAILED findings (CRITICAL/HIGH/MEDIUM)
    - Critical Findings: Only CRITICAL severity
    - High Findings: Only HIGH severity
    - Medium Findings: Only MEDIUM severity
    
    Args:
        account_scores: Dict mapping account_id to {account_name, cis_score, nist_score, cis_fail, nist_fail}
        findings_data: List of filtered finding dictionaries (already filtered to FAILED + CRITICAL/HIGH/MEDIUM)
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
    
    fail_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "num_format": "0",
        "bg_color": "#7F1D1D",
        "font_color": "#FCA5A5",
    })
    
    critical_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "bg_color": "#7F1D1D",
        "font_color": "#FCA5A5",
        "bold": True,
    })
    
    high_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "bg_color": "#7C2D12",
        "font_color": "#FDBA74",
        "bold": True,
    })
    
    medium_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "bg_color": "#854D0E",
        "font_color": "#FED7AA",
    })
    
    # ===== SHEET 1: EXECUTIVE SUMMARY =====
    summary_sheet = workbook.add_worksheet("Executive Summary")
    
    # Summary title
    summary_sheet.merge_range(0, 0, 0, 4, "CSPM Consolidated Report", header_format)
    
    row = 2
    summary_sheet.write(row, 0, "Report Date:", workbook.add_format({"bold": True}))
    summary_sheet.write(row, 1, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    
    row = 3
    summary_sheet.write(row, 0, "Selected Accounts:", workbook.add_format({"bold": True}))
    summary_sheet.write(row, 1, len(account_scores))
    
    # Count findings by severity
    has_findings = findings_data is not None and len(findings_data) > 0
    critical_count = 0
    high_count = 0
    medium_count = 0
    
    if has_findings:
        for finding in findings_data:
            severity = (finding.get("severity", "") or "").upper()
            if severity == "CRITICAL":
                critical_count += 1
            elif severity == "HIGH":
                high_count += 1
            elif severity == "MEDIUM":
                medium_count += 1
    
    row = 4
    summary_sheet.write(row, 0, "Total Failed Findings:", workbook.add_format({"bold": True}))
    summary_sheet.write(row, 1, len(findings_data) if has_findings else 0)
    
    row = 5
    summary_sheet.write(row, 0, "  - Critical:", workbook.add_format({"bold": True}))
    summary_sheet.write(row, 1, critical_count, critical_format)
    
    row = 6
    summary_sheet.write(row, 0, "  - High:", workbook.add_format({"bold": True}))
    summary_sheet.write(row, 1, high_count, high_format)
    
    row = 7
    summary_sheet.write(row, 0, "  - Medium:", workbook.add_format({"bold": True}))
    summary_sheet.write(row, 1, medium_count, medium_format)
    
    # Account summary table
    row = 9
    summary_sheet.merge_range(row, 0, row, 4, "Account Summary", header_format)
    
    row = 10
    summary_headers = ["Account ID", "Account Name", "CIS Score", "NIST Score", "Failed Controls"]
    for col, header in enumerate(summary_headers):
        summary_sheet.write(row, col, header, header_format)
    
    summary_sheet.set_column(0, 0, 16)
    summary_sheet.set_column(1, 1, 25)
    summary_sheet.set_column(2, 4, 14)
    
    row = 11
    for account_id, data in sorted(account_scores.items()):
        account_findings_count = sum(1 for f in (findings_data or []) if f.get("account_id") == account_id)
        summary_sheet.write(row, 0, account_id, data_format)
        summary_sheet.write(row, 1, data.get("account_name", account_id), data_format)
        summary_sheet.write(row, 2, data.get("cis_score", 0), score_format)
        summary_sheet.write(row, 3, data.get("nist_score", 0), score_format)
        summary_sheet.write(row, 4, account_findings_count, fail_format)
        row += 1
    
    # ===== SHEET 2: ALL FAILED FINDINGS =====
    all_failed_sheet = workbook.add_worksheet("All Failed Findings")
    _write_findings_sheet(all_failed_sheet, workbook, findings_data or [], None, header_format)
    
    # ===== SHEET 3: CRITICAL FINDINGS =====
    critical_findings = [f for f in (findings_data or []) if (f.get("severity", "") or "").upper() == "CRITICAL"]
    critical_sheet = workbook.add_worksheet("Critical Findings")
    _write_findings_sheet(critical_sheet, workbook, critical_findings, "CRITICAL", header_format)
    
    # ===== SHEET 4: HIGH FINDINGS =====
    high_findings = [f for f in (findings_data or []) if (f.get("severity", "") or "").upper() == "HIGH"]
    high_sheet = workbook.add_worksheet("High Findings")
    _write_findings_sheet(high_sheet, workbook, high_findings, "HIGH", header_format)
    
    # ===== SHEET 5: MEDIUM FINDINGS =====
    medium_findings = [f for f in (findings_data or []) if (f.get("severity", "") or "").upper() == "MEDIUM"]
    medium_sheet = workbook.add_worksheet("Medium Findings")
    _write_findings_sheet(medium_sheet, workbook, medium_findings, "MEDIUM", header_format)
    
    workbook.close()
    logger.info("cspm_report_generated", path=filename, accounts=len(account_scores), 
               total_findings=len(findings_data or []), critical=critical_count, high=high_count, medium=medium_count)
    return filename


def _write_findings_sheet(sheet, workbook, findings: list[dict], severity_filter: str | None, header_format) -> None:
    """Helper function to write findings to a sheet with consistent formatting."""
    text_format = workbook.add_format({
        "border": 1,
        "align": "left",
        "valign": "top",
        "text_wrap": True,
    })
    
    data_format = workbook.add_format({
        "border": 1,
        "align": "left",
        "valign": "vcenter",
    })
    
    critical_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "bg_color": "#7F1D1D",
        "font_color": "#FCA5A5",
        "bold": True,
    })
    
    high_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "bg_color": "#7C2D12",
        "font_color": "#FDBA74",
        "bold": True,
    })
    
    medium_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "bg_color": "#854D0E",
        "font_color": "#FED7AA",
    })
    
    # Headers
    finding_headers = [
        "Account Name",
        "Account ID",
        "Benchmark",
        "Control ID",
        "Control Title",
        "Severity",
        "Compliance Status",
        "Resource ID",
        "Region",
        "Description",
        "Remediation URL",
        "Last Updated"
    ]
    
    for col, header in enumerate(finding_headers):
        sheet.write(0, col, header, header_format)
    
    # Set column widths
    sheet.set_column(0, 0, 20)  # Account Name
    sheet.set_column(1, 1, 16)  # Account ID
    sheet.set_column(2, 2, 18)  # Benchmark
    sheet.set_column(3, 3, 20)  # Control ID
    sheet.set_column(4, 4, 30)  # Control Title
    sheet.set_column(5, 5, 12)  # Severity
    sheet.set_column(6, 6, 16)  # Compliance Status
    sheet.set_column(7, 7, 30)  # Resource ID
    sheet.set_column(8, 8, 12)  # Region
    sheet.set_column(9, 9, 35)  # Description
    sheet.set_column(10, 10, 35)  # Remediation URL
    sheet.set_column(11, 11, 16)  # Last Updated
    
    # Write findings
    row = 1
    for finding in sorted(findings, key=lambda x: (x.get("account_id", ""), x.get("severity", ""), x.get("control_id", ""))):
        severity = (finding.get("severity", "") or "").upper()
        
        # Choose severity format
        if severity == "CRITICAL":
            sev_format = critical_format
        elif severity == "HIGH":
            sev_format = high_format
        else:  # MEDIUM
            sev_format = medium_format
        
        sheet.write(row, 0, finding.get("account_name", ""), data_format)
        sheet.write(row, 1, finding.get("account_id", ""), data_format)
        sheet.write(row, 2, finding.get("benchmark", ""), data_format)
        sheet.write(row, 3, finding.get("control_id", ""), data_format)
        sheet.write(row, 4, finding.get("title", ""), text_format)
        sheet.write(row, 5, severity, sev_format)
        sheet.write(row, 6, (finding.get("compliance_status", "") or "").upper(), data_format)
        sheet.write(row, 7, finding.get("resource_id", ""), data_format)
        sheet.write(row, 8, finding.get("region", ""), data_format)
        sheet.write(row, 9, finding.get("description", ""), text_format)
        sheet.write(row, 10, finding.get("remediation_url", ""), text_format)
        sheet.write(row, 11, finding.get("last_updated", ""), data_format)
        row += 1
