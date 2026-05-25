import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.email import EmailDeliveryLog
from app.models.owner import AccountOwner, OwnerMapping
from app.services.aws.live_data import get_account_by_id, get_live_snapshot, fetch_account_inspector_findings, fetch_account_cspm_findings
from app.services.aws.s3_cspm_scores import get_cspm_scores_from_s3
from app.services.email.email_templates import get_inspector_email_template, get_cspm_email_template
from app.services.reports.inspector_cspm_reports import generate_inspector_report, generate_cspm_report
from app.services.email.graph_client import GraphMailClient

router = APIRouter()


class ComposePreviewRequest(BaseModel):
    account_ids: list[str]
    finding_type: str = "inspector"  # "inspector" or "cspm"


class SendEmailRequest(BaseModel):
    account_ids: list[str]
    finding_type: str = "inspector"  # "inspector" or "cspm"
    to_emails: list[EmailStr]
    cc_emails: list[EmailStr] = []
    subject: str
    body_html: str
    confirmed: bool = False


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
    
    finding_type = payload.finding_type.lower()
    if finding_type not in ["inspector", "cspm"]:
        raise HTTPException(400, "finding_type must be 'inspector' or 'cspm'")

    snapshot = await get_live_snapshot(force=False)
    account_rows = [get_account_by_id(snapshot.get("accounts", []), aid) for aid in payload.account_ids]
    account_rows = [r for r in account_rows if r]

    if not account_rows:
        raise HTTPException(400, "No valid accounts found")

    names = [r.get("account_name", r.get("account_id")) for r in account_rows]
    suggested_to = await _resolve_owner_emails(session, payload.account_ids)

    if finding_type == "inspector":
        # Parallel fetch for Inspector findings
        inspector_data = await asyncio.gather(
            *[fetch_account_inspector_findings(aid, r.get("account_name")) 
              for aid, r in zip(payload.account_ids, account_rows)],
            return_exceptions=True
        )
        
        account_findings = {}
        for account_id, data in zip(payload.account_ids, inspector_data):
            if isinstance(data, Exception):
                continue
            if data.get("status") == "completed":
                findings = data.get("findings", [])
                stats = data.get("stats", {})
                account_findings[account_id] = {
                    "account_name": data.get("account_name", account_id),
                    "critical": stats.get("critical", 0),
                    "high": stats.get("high", 0),
                    "total": stats.get("total", 0),
                    "coverage": stats.get("coverage", 0),
                }
        
        body_html = get_inspector_email_template(account_findings)
        subject = f"AWS Inspector Findings Report — {', '.join(names[:2])}" + (f" (+{len(names)-2} more)" if len(names) > 2 else "")
    
    else:  # CSPM
        # Fetch CSPM scores from S3 (with fallback to live data)
        scores_result = await get_cspm_scores_from_s3()
        cspm_all_scores = scores_result.get("scores", {})
        
        cspm_security_score = 0
        if cspm_all_scores:
            # Calculate average security score from all accounts
            cis_scores = [score.get('cis_score', 0) for score in cspm_all_scores.values()]
            nist_scores = [score.get('nist_score', 0) for score in cspm_all_scores.values()]
            cspm_security_score = (sum(cis_scores + nist_scores) / (len(cis_scores + nist_scores))) if (cis_scores + nist_scores) else 0
        
        account_scores = {aid: cspm_all_scores.get(aid, {
            "cis_score": 0, "nist_score": 0, "cis_pass": 0, "cis_fail": 0, "nist_pass": 0, "nist_fail": 0
        }) for aid in payload.account_ids}
        
        # Enrich with account names
        for aid, data in account_scores.items():
            account = next((r for r in account_rows if r.get("account_id") == aid), {})
            data["account_name"] = account.get("account_name", aid)
        
        body_html = get_cspm_email_template(account_scores, cspm_security_score=cspm_security_score)
        subject = f"AWS CSPM Compliance Report — {', '.join(names[:2])}" + (f" (+{len(names)-2} more)" if len(names) > 2 else "")

    return {
        "subject": subject,
        "body_html": body_html,
        "suggested_to": suggested_to,
        "account_rows": account_rows,
        "finding_type": finding_type,
    }


@router.post("/send")
async def send_email(payload: SendEmailRequest, session: AsyncSession = Depends(get_db)):
    if not payload.confirmed:
        raise HTTPException(400, "Email send requires confirmed=true after user confirmation")
    if not payload.account_ids:
        raise HTTPException(400, "Select at least one account")
    if not payload.to_emails:
        raise HTTPException(400, "At least one recipient required")
    
    finding_type = payload.finding_type.lower()
    if finding_type not in ["inspector", "cspm"]:
        raise HTTPException(400, "finding_type must be 'inspector' or 'cspm'")

    snapshot = await get_live_snapshot(force=False)
    account_rows = [get_account_by_id(snapshot.get("accounts", []), aid) for aid in payload.account_ids]
    account_rows = [r for r in account_rows if r]
    
    if not account_rows:
        raise HTTPException(400, "No valid accounts found")
    
    attachment_path = None
    status = "failed"
    error: str | None = None
    
    try:
        if finding_type == "inspector":
            # Parallel fetch for Inspector findings (optimized)
            inspector_results = await asyncio.gather(
                *[fetch_account_inspector_findings(aid, r.get("account_name")) 
                  for aid, r in zip(payload.account_ids, account_rows)],
                return_exceptions=True
            )
            
            account_findings = {}
            all_findings = []
            for account_id, result in zip(payload.account_ids, inspector_results):
                if isinstance(result, Exception):
                    continue
                if result.get("status") == "completed":
                    stats = result.get("stats", {})
                    account_findings[account_id] = {
                        "account_name": result.get("account_name", account_id),
                        "critical": stats.get("critical", 0),
                        "high": stats.get("high", 0),
                        "total": stats.get("total", 0),
                        "coverage": stats.get("coverage", 0),
                    }
                    # Collect all findings for detailed report
                    all_findings.extend(result.get("findings", []))
            
            if not account_findings:
                raise Exception("No findings retrieved from Inspector")
            
            # Generate Inspector report with detailed findings
            attachment_path = generate_inspector_report(account_findings, findings_data=all_findings)
        
        else:  # CSPM
            # Fetch CSPM findings for detailed report
            cspm_results = await asyncio.gather(
                *[fetch_account_cspm_findings(aid, r.get("account_name")) 
                  for aid, r in zip(payload.account_ids, account_rows)],
                return_exceptions=True
            )
            
            # Fetch CSPM security score from S3 (with fallback to live data)
            scores_result = await get_cspm_scores_from_s3()
            cspm_all_scores = scores_result.get("scores", {})
            cspm_security_score = 0
            if cspm_all_scores:
                # Calculate average security score from all accounts
                cis_scores = [score.get('cis_score', 0) for score in cspm_all_scores.values()]
                nist_scores = [score.get('nist_score', 0) for score in cspm_all_scores.values()]
                cspm_security_score = (sum(cis_scores + nist_scores) / (len(cis_scores + nist_scores))) if (cis_scores + nist_scores) else 0
            
            account_scores = {}
            all_findings = []
            for account_id, result in zip(payload.account_ids, cspm_results):
                if isinstance(result, Exception):
                    continue
                if result.get("status") == "completed":
                    findings = result.get("findings", [])
                    stats = result.get("stats", {})
                    account_scores[account_id] = {
                        "account_name": result.get("account_name", account_id),
                        "cis_score": stats.get("cis_score", 0),
                        "nist_score": stats.get("nist_score", 0),
                        "cis_pass": sum(1 for f in findings if f.get("benchmark") == "cis-aws-foundations-benchmark" and f.get("compliance_status") == "PASSED"),
                        "cis_fail": sum(1 for f in findings if f.get("benchmark") == "cis-aws-foundations-benchmark" and f.get("compliance_status") != "PASSED"),
                        "nist_pass": sum(1 for f in findings if f.get("benchmark") == "nist-800-53" and f.get("compliance_status") == "PASSED"),
                        "nist_fail": sum(1 for f in findings if f.get("benchmark") == "nist-800-53" and f.get("compliance_status") != "PASSED"),
                    }
                    # Collect all findings for detailed report
                    all_findings.extend(findings)
            
            if not account_scores:
                raise Exception("No CSPM findings found")
            
            # Generate CSPM report with detailed findings and include CSPM security score in email body
            attachment_path = generate_cspm_report(account_scores, findings_data=all_findings)
            
            # Update email body to include CSPM security score
            payload.body_html = get_cspm_email_template(account_scores, cspm_security_score=cspm_security_score)
        
        # Send email
        mail = GraphMailClient()
        await mail.send_mail(
            to_emails=[str(e) for e in payload.to_emails],
            cc_emails=[str(e) for e in payload.cc_emails],
            subject=payload.subject,
            html_body=payload.body_html,
            attachments=[attachment_path] if attachment_path else [],
        )
        status = "sent"
    
    except Exception as exc:
        error = str(exc)

    # Log email delivery
    sent_month = datetime.now(timezone.utc).strftime("%Y-%m")
    log = EmailDeliveryLog(
        recipient_email=",".join(str(e) for e in payload.to_emails),
        subject=payload.subject,
        status=status,
        account_ids=json.dumps(payload.account_ids),
        attachments=json.dumps([attachment_path] if attachment_path else []),
        cc_emails=",".join(str(e) for e in payload.cc_emails) if payload.cc_emails else None,
        html_body=payload.body_html[:8000] if payload.body_html else None,
        sent_month=sent_month,
        sent_at=datetime.now(timezone.utc) if status == "sent" else None,
        error_message=error,
    )
    session.add(log)
    await session.flush()
    await session.commit()
    
    if status == "failed":
        raise HTTPException(500, f"Failed to send email: {error}")
    
    return {
        "status": "sent",
        "message": "Email sent successfully",
        "log_id": log.id,
        "timestamp": sent_month,
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
