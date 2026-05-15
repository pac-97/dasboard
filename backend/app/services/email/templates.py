from datetime import datetime, timezone


def _scorecard(label: str, color: str, value: str) -> str:
    return (
        '<td width="25%" style="padding:8px;">'
        '<div style="background:#1E293B;border-radius:12px;padding:16px;text-align:center;">'
        f'<div style="color:#94A3B8;font-size:11px;">{label}</div>'
        f'<div style="color:{color};font-size:28px;font-weight:700;">{value}</div>'
        "</div></td>"
    )


def build_owner_email_html(
    owner_name: str,
    accounts: list[dict],
    inspector_summary: dict,
    cspm_summary: dict,
) -> str:
    account_rows = "".join(
        f"""<tr>
          <td style="padding:12px;border-bottom:1px solid #1E293B;color:#E2E8F0;">{a.get('account_name', a.get('account_id'))}</td>
          <td style="padding:12px;border-bottom:1px solid #1E293B;color:#EF4444;font-weight:600;">{a.get('critical', 0)}</td>
          <td style="padding:12px;border-bottom:1px solid #1E293B;color:#F97316;font-weight:600;">{a.get('high', 0)}</td>
          <td style="padding:12px;border-bottom:1px solid #1E293B;color:#22C55E;">{a.get('cis_score', 'N/A')}%</td>
          <td style="padding:12px;border-bottom:1px solid #1E293B;color:#38BDF8;">{a.get('nist_score', 'N/A')}%</td>
        </tr>"""
        for a in accounts
    )

    cards = "".join(
        [
            _scorecard("CRITICAL", "#EF4444", str(inspector_summary.get("critical", 0))),
            _scorecard("HIGH", "#F97316", str(inspector_summary.get("high", 0))),
            _scorecard("CIS", "#22C55E", f"{cspm_summary.get('cis_score', 0)}%"),
            _scorecard("NIST", "#38BDF8", f"{cspm_summary.get('nist_score', 0)}%"),
        ]
    )

    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;background:#0B1220;font-family:Segoe UI,system-ui,sans-serif;">
<table width="100%" style="padding:32px 16px;"><tr><td align="center">
<table width="640" style="background:#0F172A;border-radius:16px;border:1px solid #1E293B;">
<tr><td style="background:linear-gradient(135deg,#1D4ED8,#7C3AED);padding:32px;">
<h1 style="margin:0;color:#FFF;font-size:24px;">AWS Security Posture Report</h1>
<p style="margin:8px 0 0;color:#BFDBFE;">{date_str} · {owner_name}</p>
</td></tr>
<tr><td style="padding:32px;">
<table width="100%"><tr>{cards}</tr></table>
<h2 style="color:#F8FAFC;font-size:18px;margin:32px 0 16px;">Account Breakdown</h2>
<table width="100%" style="border-collapse:collapse;">
<tr style="background:#1E293B;">
<th style="padding:12px;text-align:left;color:#94A3B8;">Account</th>
<th style="padding:12px;text-align:left;color:#94A3B8;">Critical</th>
<th style="padding:12px;text-align:left;color:#94A3B8;">High</th>
<th style="padding:12px;text-align:left;color:#94A3B8;">CIS</th>
<th style="padding:12px;text-align:left;color:#94A3B8;">NIST</th>
</tr>
{account_rows}
</table>
<p style="color:#64748B;font-size:12px;margin-top:32px;">Inspector and CSPM reports are attached.</p>
</td></tr>
</table>
</td></tr></table>
</body></html>"""
