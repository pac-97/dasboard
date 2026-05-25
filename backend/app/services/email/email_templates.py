"""Email templates for Inspector and CSPM findings."""

from datetime import datetime, timezone


def get_inspector_email_template(account_findings: dict[str, dict]) -> str:
    """
    Generate HTML email template for Inspector findings.
    
    Args:
        account_findings: Dict mapping account_id to {
            account_name: str,
            critical: int,
            high: int,
            total: int,
            coverage: float (%)
        }
    
    Returns:
        HTML email body
    """
    rows_html = "".join(
        f"""<tr>
            <td style="padding:12px;border:1px solid #475569;text-align:left;">{account_id}</td>
            <td style="padding:12px;border:1px solid #475569;text-align:left;">{data.get('account_name', account_id)}</td>
            <td style="padding:12px;border:1px solid #475569;text-align:center;">{data.get('coverage', 0):.1f}%</td>
            <td style="padding:12px;border:1px solid #475569;text-align:center;color:#FCA5A5;font-weight:bold;">{data.get('critical', 0)}</td>
            <td style="padding:12px;border:1px solid #475569;text-align:center;color:#FDBA74;font-weight:bold;">{data.get('high', 0)}</td>
            <td style="padding:12px;border:1px solid #475569;text-align:center;font-weight:bold;">{data.get('total', 0)}</td>
        </tr>"""
        for account_id, data in sorted(account_findings.items())
    )
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0F172A; color: #E2E8F0; line-height: 1.6; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 20px; background-color: #1A202C; border-radius: 8px; }}
        .header {{ border-bottom: 2px solid #334155; padding-bottom: 16px; margin-bottom: 24px; }}
        .header h1 {{ margin: 0; color: #60A5FA; font-size: 24px; }}
        .header p {{ margin: 4px 0; color: #94A3B8; font-size: 14px; }}
        .section {{ margin-bottom: 24px; }}
        .section h2 {{ color: #F1F5F9; font-size: 16px; margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; background-color: #0F172A; }}
        thead tr {{ background-color: #1E293B; }}
        thead th {{ padding: 12px; text-align: left; color: #E2E8F0; font-weight: 600; border: 1px solid #475569; }}
        tbody td {{ padding: 10px 12px; border: 1px solid #475569; }}
        tbody tr:nth-child(even) {{ background-color: #111827; }}
        tbody tr:hover {{ background-color: #1F2937; }}
        .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #334155; color: #64748B; font-size: 12px; text-align: center; }}
        .metric {{ display: inline-block; margin: 0 12px 0 0; }}
        .critical {{ color: #FCA5A5; font-weight: bold; }}
        .high {{ color: #FDBA74; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AWS Inspector Findings Report</h1>
            <p>Vulnerability Assessment Summary</p>
        </div>
        
        <div class="section">
            <h2>Findings Summary</h2>
            <p>The following table shows Inspector vulnerability findings for your account(s):</p>
            <table>
                <thead>
                    <tr>
                        <th>Account Number</th>
                        <th>Account Name</th>
                        <th>Inspector Coverage</th>
                        <th style="color: #FCA5A5;">Critical</th>
                        <th style="color: #FDBA74;">High</th>
                        <th>All</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>Key Metrics</h2>
            <div class="metric"><strong>Total Accounts:</strong> {len(account_findings)}</div>
            <div class="metric"><strong>Total Critical:</strong> <span class="critical">{sum(d.get('critical', 0) for d in account_findings.values())}</span></div>
            <div class="metric"><strong>Total High:</strong> <span class="high">{sum(d.get('high', 0) for d in account_findings.values())}</span></div>
            <div class="metric"><strong>Total Findings:</strong> {sum(d.get('total', 0) for d in account_findings.values())}</div>
        </div>
        
        <div class="section">
            <h2>What's Included</h2>
            <p><strong>This is an AWS Inspector ONLY report.</strong> All Inspector vulnerability findings are included in the attached XLSX file with complete details for each finding.</p>
            <ul>
                <li>Summary statistics by account (above table)</li>
                <li><strong>Detailed Findings Sheet:</strong> All Inspector findings with severity, description, affected resources, remediation steps, and more</li>
                <li>Coverage percentage indicates the portion of your resources scanned for vulnerabilities</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>Action Required</h2>
            <p>Please review the attached XLSX report for detailed findings and take appropriate remediation actions.</p>
            <ul>
                <li><strong>Critical Findings:</strong> Address immediately to reduce security risk</li>
                <li><strong>High Findings:</strong> Address within short timeframe (30 days)</li>
                <li><strong>Coverage %:</strong> Higher coverage provides more comprehensive vulnerability detection</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p>This is an automated report from AWS Security Dashboard</p>
        </div>
    </div>
</body>
</html>"""


def get_cspm_email_template(account_scores: dict[str, dict], cspm_security_score: float = 0) -> str:
    """
    Generate HTML email template for CSPM compliance scores.
    
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
        cspm_security_score: Overall CSPM security score from S3 (0-100)
    
    Returns:
        HTML email body
    """
    rows_html = "".join(
        f"""<tr>
            <td style="padding:12px;border:1px solid #475569;text-align:left;">{account_id}</td>
            <td style="padding:12px;border:1px solid #475569;text-align:left;">{data.get('account_name', account_id)}</td>
            <td style="padding:12px;border:1px solid #475569;text-align:center;color:#60A5FA;">{data.get('cis_score', 0):.1f}%</td>
            <td style="padding:12px;border:1px solid #475569;text-align:center;color:#86EFAC;">{data.get('cis_pass', 0)}</td>
            <td style="padding:12px;border:1px solid #475569;text-align:center;color:#FCA5A5;">{data.get('cis_fail', 0)}</td>
            <td style="padding:12px;border:1px solid #475569;text-align:center;color:#10B981;">{data.get('nist_score', 0):.1f}%</td>
            <td style="padding:12px;border:1px solid #475569;text-align:center;color:#86EFAC;">{data.get('nist_pass', 0)}</td>
            <td style="padding:12px;border:1px solid #475569;text-align:center;color:#FCA5A5;">{data.get('nist_fail', 0)}</td>
        </tr>"""
        for account_id, data in sorted(account_scores.items())
    )
    
    avg_cis = sum(d.get('cis_score', 0) for d in account_scores.values()) / len(account_scores) if account_scores else 0
    avg_nist = sum(d.get('nist_score', 0) for d in account_scores.values()) / len(account_scores) if account_scores else 0
    
    # Determine score color based on value
    cspm_color = "#10B981" if cspm_security_score >= 70 else "#F59E0B" if cspm_security_score >= 50 else "#EF4444"
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0F172A; color: #E2E8F0; line-height: 1.6; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 20px; background-color: #1A202C; border-radius: 8px; }}
        .header {{ border-bottom: 2px solid #334155; padding-bottom: 16px; margin-bottom: 24px; }}
        .header h1 {{ margin: 0; color: #34D399; font-size: 24px; }}
        .header p {{ margin: 4px 0; color: #94A3B8; font-size: 14px; }}
        .section {{ margin-bottom: 24px; }}
        .section h2 {{ color: #F1F5F9; font-size: 16px; margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; background-color: #0F172A; }}
        thead tr {{ background-color: #1E293B; }}
        thead th {{ padding: 12px; text-align: left; color: #E2E8F0; font-weight: 600; border: 1px solid #475569; }}
        tbody td {{ padding: 10px 12px; border: 1px solid #475569; }}
        tbody tr:nth-child(even) {{ background-color: #111827; }}
        tbody tr:hover {{ background-color: #1F2937; }}
        .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #334155; color: #64748B; font-size: 12px; text-align: center; }}
        .metrics {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 12px 0; }}
        .metric-box {{ padding: 12px; background-color: #1E293B; border-radius: 6px; border-left: 4px solid #34D399; }}
        .metric-label {{ color: #94A3B8; font-size: 12px; text-transform: uppercase; }}
        .metric-value {{ color: #34D399; font-size: 24px; font-weight: bold; margin-top: 4px; }}
        .cspm-score {{ border-left-color: {cspm_color}; }}
        .cspm-value {{ color: {cspm_color}; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CSPM Compliance Report</h1>
            <p>Cloud Security Posture Management Assessment</p>
        </div>
        
        <div class="section">
            <h2>Overall Security Posture</h2>
            <div class="metrics">
                <div class="metric-box cspm-score">
                    <div class="metric-label">CSPM Security Score</div>
                    <div class="metric-value cspm-value">{cspm_security_score:.1f}/100</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Total Accounts</div>
                    <div class="metric-value">{len(account_scores)}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">CIS AWS Foundations Benchmark v5.0.0</div>
                    <div class="metric-value">{avg_cis:.1f}%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">NIST Special Publication 800-53 Revision 5</div>
                    <div class="metric-value">{avg_nist:.1f}%</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Benchmark Compliance by Account</h2>
            <p>The following table shows your compliance posture against CIS AWS Foundations Benchmark v5.0.0 and NIST Special Publication 800-53 Revision 5:</p>
            <table>
                <thead>
                    <tr>
                        <th>Account Number</th>
                        <th>Account Name</th>
                        <th style="color: #60A5FA;">CIS AWS v5.0.0 %</th>
                        <th style="color: #86EFAC;">CIS Pass</th>
                        <th style="color: #FCA5A5;">CIS Fail</th>
                        <th style="color: #10B981;">NIST 800-53 R5 %</th>
                        <th style="color: #86EFAC;">NIST Pass</th>
                        <th style="color: #FCA5A5;">NIST Fail</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>What's Included</h2>
            <p><strong>This is a CSPM (Cloud Security Posture Management) ONLY report.</strong> All compliance findings are included in the attached XLSX file with complete details for each control.</p>
            <ul>
                <li><strong>Overall CSPM Security Score:</strong> Organization-wide security posture metric</li>
                <li><strong>CIS AWS Foundations Benchmark v5.0.0:</strong> Compliance percentage and pass/fail counts per account</li>
                <li><strong>NIST Special Publication 800-53 Revision 5:</strong> Compliance percentage and pass/fail counts per account</li>
                <li><strong>Detailed Findings Sheet:</strong> All failed and passed controls with benchmark, control ID, severity, description, and remediation details</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>Benchmark Framework Details</h2>
            <ul>
                <li><strong>CIS AWS Foundations Benchmark v5.0.0:</strong> Center for Internet Security best practices for AWS cloud security</li>
                <li><strong>NIST Special Publication 800-53 Revision 5:</strong> National Institute of Standards & Technology Security and Privacy Controls</li>
                <li><strong>Pass/Fail:</strong> Number of passed and failed controls per benchmark per account</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p>This is an automated report from AWS Security Dashboard</p>
        </div>
    </div>
</body>
</html>"""
