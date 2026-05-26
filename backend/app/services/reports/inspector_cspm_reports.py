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
    Generate CSPM-only XLSX report with summary and detailed findings.
    
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
        findings_data: List of detailed finding dictionaries (optional)
        output_path: Optional custom output path
    
    Returns:
        Path to generated XLSX file
    """
    logger.info("generate_cspm_report_start", findings_data_count=len(findings_data) if findings_data else 0, 
                findings_data_is_none=findings_data is None, findings_data_type=type(findings_data).__name__)
    
    settings = get_settings()
    out_dir = Path(settings.reports_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = output_path or str(
        out_dir / f"cspm_report_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.xlsx"
    )

    workbook = xlsxwriter.Workbook(filename)
    
    # Single worksheet with summary and findings
    report_sheet = workbook.add_worksheet("CSPM Report")
    
    # Calculate pass/fail counts from findings data
    has_findings = findings_data is not None and len(findings_data) > 0
    if has_findings:
        # Calculate CIS and NIST pass/fail from findings
        for account_id in account_scores:
            cis_pass = 0
            cis_fail = 0
            nist_pass = 0
            nist_fail = 0
            
            for finding in findings_data:
                if finding.get("account_id") == account_id:
                    benchmark = (finding.get("benchmark") or "").lower()
                    status = (finding.get("compliance_status") or "").upper()
                    
                    if "cis" in benchmark:
                        if status == "FAILED":
                            cis_fail += 1
                        elif status == "PASSED":
                            cis_pass += 1
                    elif "nist" in benchmark:
                        if status == "FAILED":
                            nist_fail += 1
                        elif status == "PASSED":
                            nist_pass += 1
            
            # Update account_scores with calculated counts
            if cis_pass > 0 or cis_fail > 0 or nist_pass > 0 or nist_fail > 0:
                account_scores[account_id]["cis_pass"] = cis_pass
                account_scores[account_id]["cis_fail"] = cis_fail
                account_scores[account_id]["nist_pass"] = nist_pass
                account_scores[account_id]["nist_fail"] = nist_fail
                logger.info("cspm_report_calculated_counts", account_id=account_id, 
                           cis_pass=cis_pass, cis_fail=cis_fail, nist_pass=nist_pass, nist_fail=nist_fail)
    
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
    
    # ===== CSPM REPORT SHEET (Summary + Actionable Findings) =====
    # Headers for summary
    headers = ["Account Number", "Account Name", "CIS Score", "CIS Fail", "NIST Score", "NIST Fail"]
    for col, header in enumerate(headers):
        report_sheet.write(0, col, header, header_format)
    
    # Set column widths for summary
    report_sheet.set_column(0, 0, 16)
    report_sheet.set_column(1, 1, 25)
    report_sheet.set_column(2, 5, 14)
    
    # Data rows for summary
    row = 1
    for account_id, data in sorted(account_scores.items()):
        report_sheet.write(row, 0, account_id, data_format)
        report_sheet.write(row, 1, data.get("account_name", account_id), data_format)
        report_sheet.write(row, 2, data.get("cis_score", 0), score_format)
        report_sheet.write(row, 3, data.get("cis_fail", 0), fail_format)
        report_sheet.write(row, 4, data.get("nist_score", 0), score_format)
        report_sheet.write(row, 5, data.get("nist_fail", 0), fail_format)
        row += 1
    
    # Add blank row separator
    findings_start_row = row + 2
    
    # ===== ACTIONABLE FINDINGS SECTION =====
    if findings_data:
        # Formats for compliance status
        passed_format = workbook.add_format({
            "border": 1,
            "align": "left",
            "bg_color": "#064E3B",
            "font_color": "#86EFAC",
            "text_wrap": True,
        })
        
        failed_format = workbook.add_format({
            "border": 1,
            "align": "left",
            "bg_color": "#7F1D1D",
            "font_color": "#FCA5A5",
            "text_wrap": True,
        })
        
        text_format = workbook.add_format({
            "border": 1,
            "align": "left",
            "valign": "top",
            "text_wrap": True,
        })
        
        # Headers for actionable findings (FAILED + CRITICAL/HIGH/MEDIUM only)
        finding_headers = [
            "Account ID",
            "Account Name",
            "Benchmark",
            "Control ID",
            "Control Title",
            "Status",
            "Severity",
            "Region",
            "Resource ID",
            "Description",
            "Remediation"
        ]
        
        # Write headers to actionable findings section
        for col, header in enumerate(finding_headers):
            report_sheet.write(findings_start_row, col, header, header_format)
        
        # Set column widths for actionable findings section
        report_sheet.set_column(0, 0, 16)  # Account ID
        report_sheet.set_column(1, 1, 25)  # Account Name
        report_sheet.set_column(2, 2, 18)  # Benchmark
        report_sheet.set_column(3, 3, 20)  # Control ID
        report_sheet.set_column(4, 4, 30)  # Control Title
        report_sheet.set_column(5, 5, 14)  # Status
        report_sheet.set_column(6, 6, 12)  # Severity
        report_sheet.set_column(7, 7, 12)  # Region
        report_sheet.set_column(8, 8, 30)  # Resource ID
        report_sheet.set_column(9, 9, 40)  # Description
        report_sheet.set_column(10, 10, 40)  # Remediation
        
        # Write findings data - all are already filtered to FAILED + CRITICAL/HIGH/MEDIUM
        row = findings_start_row + 1
        logger.info("cspm_report_writing_findings", findings_count=len(findings_data), first_finding=findings_data[0] if findings_data else None)
        for finding in sorted(findings_data, key=lambda x: (x.get("account_id", ""), x.get("benchmark", ""), x.get("control_id", ""))):
            severity = (finding.get("severity", "") or "").upper()
            
            # Format severity columns with color coding
            if severity == "CRITICAL":
                severity_format = workbook.add_format({
                    "border": 1,
                    "align": "center",
                    "bg_color": "#7F1D1D",
                    "font_color": "#FCA5A5",
                    "bold": True,
                })
            elif severity == "HIGH":
                severity_format = workbook.add_format({
                    "border": 1,
                    "align": "center",
                    "bg_color": "#7C2D12",
                    "font_color": "#FDBA74",
                    "bold": True,
                })
            else:  # MEDIUM
                severity_format = workbook.add_format({
                    "border": 1,
                    "align": "center",
                    "bg_color": "#854D0E",
                    "font_color": "#FED7AA",
                })
            
            # Write to CSPM Report sheet
            report_sheet.write(row, 0, finding.get("account_id", ""), data_format)
            report_sheet.write(row, 1, finding.get("account_name", ""), data_format)
            report_sheet.write(row, 2, finding.get("benchmark", ""), data_format)
            report_sheet.write(row, 3, finding.get("control_id", ""), data_format)
            report_sheet.write(row, 4, finding.get("title", ""), text_format)
            report_sheet.write(row, 5, (finding.get("compliance_status", "") or "").upper(), data_format)
            report_sheet.write(row, 6, severity, severity_format)
            report_sheet.write(row, 7, finding.get("region", ""), data_format)
            report_sheet.write(row, 8, finding.get("resource_id", ""), data_format)
            report_sheet.write(row, 9, finding.get("description", ""), text_format)
            report_sheet.write(row, 10, finding.get("remediation_url", ""), text_format)
            row += 1
    
    workbook.close()
    if findings_data:
        logger.info("cspm_report_generated", path=filename, accounts=len(account_scores), 
                   actionable_findings_count=row-1)
    else:
        logger.info("cspm_report_generated", path=filename, accounts=len(account_scores), 
                   actionable_findings_count=0)
    return filename
