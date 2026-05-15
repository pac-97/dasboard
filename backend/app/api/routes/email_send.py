import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.email import EmailDeliveryLog
from app.models.owner import AccountOwner, OwnerMapping
from app.services.aws.live_data import filter_findings_for_accounts, get_account_row, get_live_snapshot
from app.services.charts.account_chart import generate_multi_account_chart
from app.services.email.graph_client import GraphMailClient
from app.services.reports.combined_report import generate_combined_account_report

router = APIRouter()


class ComposePreviewRequest(BaseModel):
    account_ids: list[str]


class SendEmailRequest(BaseModel):
    account_ids: list[str]
    to_emails: list[EmailStr]
    cc_emails: list[EmailStr] = []
    subject: str
    body_html: str
    confirmed: bool = False


def _default_subject(account_names: list[str]) -> str:
    if len(account_names) == 1:
        return f"AWS Security Findings Report — {account_names[0]}"
    return f"AWS Security Findings Report — {len(account_names)} Accounts"


def _default_body(account_rows: list[dict]) -> str:
    rows_html = "".join(
        f"<tr><td style='padding:8px;border:1px solid #334155;'>{a.get('account_name')}</td>"
        f"<td style='padding:8px;border:1px solid #334155;'>{a.get('inspector_total', 0)}</td>"
        f"<td style='padding:8px;border:1px solid #334155;color:#EF4444;'>{a.get('inspector_critical', 0)}</td>"
        f"<td style='padding:8px;border:1px solid #334155;color:#F97316;'>{a.get('inspector_high', 0)}</td>"
        f"<td style='padding:8px;border:1px solid #334155;'>{a.get('cspm_score', 0)}%</td></tr>"
        for a in account_rows
    )
    return f"""<html><body style="font-family:Segoe UI,sans-serif;background:#0F172A;color:#E2E8F0;padding:24px;">
<h2>AWS Security Findings Summary</h2>
<p>Please find attached the detailed XLSX report and findings chart for your account(s).</p>
<table style="border-collapse:collapse;width:100%;max-width:720px;">
<tr style="background:#1E293B;"><th style="padding:8px;">Account</th><th>Inspector</th><th>Critical</th><th>High</th><th>CSPM Score</th></tr>
{rows_html}
</table>
<p style="color:#94A3B8;font-size:12px;">Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
</body></html>"""


async def _resolve_owner_emails(session: AsyncSession, account_ids: list[str]) -> list[str]:
    emails: list[str] = []
    for aid in account_ids:
        result = await session.execute(
            select(AccountOwner.email)
            .join(OwnerMapping, OwnerMapping.owner_id == AccountOwner.id)
            .where(OwnerMapping.account_id == aid)
        )
        row = result.first()
        if row and row[0] not in emails:
            emails.append(row[0])
    return emails


@router.post("/compose-preview")
async def compose_preview(payload: ComposePreviewRequest, session: AsyncSession = Depends(get_db)):
    if not payload.account_ids:
        raise HTTPException(400, "Select at least one account")

    snapshot = await get_live_snapshot(force=False)
    account_rows = [get_account_row(snapshot, aid) for aid in payload.account_ids]
    account_rows = [r for r in account_rows if r]

    names = [r.get("account_name", r.get("account_id")) for r in account_rows]
    suggested_to = await _resolve_owner_emails(session, payload.account_ids)

    return {
        "subject": _default_subject(names),
        "body_html": _default_body(account_rows),
        "suggested_to": suggested_to,
        "account_rows": account_rows,
    }


@router.post("/send")
async def send_email(payload: SendEmailRequest, session: AsyncSession = Depends(get_db)):
    if not payload.confirmed:
        raise HTTPException(400, "Email send requires confirmed=true after user confirmation")
    if not payload.account_ids:
        raise HTTPException(400, "Select at least one account")
    if not payload.to_emails:
        raise HTTPException(400, "At least one recipient required")

    snapshot = await get_live_snapshot(force=True)
    inspector, cspm = filter_findings_for_accounts(snapshot, payload.account_ids)
    account_rows = [get_account_row(snapshot, aid) for aid in payload.account_ids]
    account_rows = [r for r in account_rows if r]

    xlsx_path = generate_combined_account_report(
        payload.account_ids, inspector, cspm, snapshot
    )
    chart_path = generate_multi_account_chart(account_rows)

    status = "failed"
    error: str | None = None
    try:
        mail = GraphMailClient()
        await mail.send_mail(
            to_emails=[str(e) for e in payload.to_emails],
            cc_emails=[str(e) for e in payload.cc_emails],
            subject=payload.subject,
            html_body=payload.body_html,
            attachments=[xlsx_path, chart_path],
        )
        status = "sent"
    except Exception as exc:
        error = str(exc)

    sent_month = datetime.now(timezone.utc).strftime("%Y-%m")
    log = EmailDeliveryLog(
        recipient_email=",".join(str(e) for e in payload.to_emails),
        subject=payload.subject,
        status=status,
        account_ids=json.dumps(payload.account_ids),
        attachments=json.dumps([xlsx_path, chart_path]),
        cc_emails=",".join(str(e) for e in payload.cc_emails) if payload.cc_emails else None,
        html_body=payload.body_html[:8000] if payload.body_html else None,
        sent_month=sent_month,
        sent_at=datetime.now(timezone.utc) if status == "sent" else None,
        error_message=error,
    )
    session.add(log)
    await session.flush()

    if status != "sent":
        raise HTTPException(500, f"Failed to send email: {error}")

    return {
        "status": "sent",
        "message": "Email sent successfully",
        "attachments": [xlsx_path, chart_path],
        "log_id": log.id,
    }


@router.get("/logs")
async def email_logs(
    month: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    query = select(EmailDeliveryLog).order_by(EmailDeliveryLog.created_at.desc())
    if month:
        try:
            year, mon = month.split("-")
            query = query.where(
                EmailDeliveryLog.sent_month == month
            ) if hasattr(EmailDeliveryLog, "sent_month") else query.where(
                extract("year", EmailDeliveryLog.created_at) == int(year),
                extract("month", EmailDeliveryLog.created_at) == int(mon),
            )
        except ValueError:
            raise HTTPException(400, "month must be YYYY-MM")

    result = await session.execute(query.limit(500))
    logs = result.scalars().all()

    by_month: dict[str, list] = {}
    for log in logs:
        key = getattr(log, "sent_month", None) or (
            log.created_at.strftime("%Y-%m") if log.created_at else "unknown"
        )
        by_month.setdefault(key, []).append(
            {
                "id": log.id,
                "recipient": log.recipient_email,
                "cc": getattr(log, "cc_emails", None),
                "subject": log.subject,
                "status": log.status,
                "account_ids": json.loads(log.account_ids) if log.account_ids else [],
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "error_message": log.error_message,
            }
        )

    return {"months": sorted(by_month.keys(), reverse=True), "logs_by_month": by_month}
