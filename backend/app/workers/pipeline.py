import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.job import JobRun, JobStatus, JobType
from app.services.analytics.dashboard import build_account_summaries
from app.services.aws.inspector import fetch_inspector_findings
from app.services.aws.organizations import list_organization_accounts
from app.services.aws.s3_findings import fetch_findings_count_history
from app.services.aws.security_hub import CIS_BENCHMARK, NIST_BENCHMARK, fetch_cspm_findings
from app.services.charts.trend_charts import generate_compliance_trend_chart, generate_findings_trend_chart
from app.services.email.graph_client import GraphMailClient
from app.services.email.templates import build_owner_email_html
from app.services.owners.consolidation import UNASSIGNED_OWNER_EMAIL, consolidate_by_owner, load_owner_account_map
from app.services.reports.cspm_report import generate_cspm_report
from app.services.reports.inspector_report import generate_inspector_report

logger = get_logger(__name__)


async def run_full_pipeline(session: AsyncSession, job: JobRun, triggered_by: str = "scheduler") -> JobRun:
    job.status = JobStatus.RUNNING.value
    job.started_at = datetime.now(timezone.utc)
    job.triggered_by = triggered_by
    await session.flush()

    try:
        accounts = list_organization_accounts()
        account_names = {a["account_id"]: a.get("account_name") for a in accounts}

        inspector_findings = fetch_inspector_findings()
        cspm_findings = fetch_cspm_findings()
        s3_snapshots = fetch_findings_count_history()

        summaries = build_account_summaries(inspector_findings, cspm_findings, account_names)
        owner_map = await load_owner_account_map(session)
        owner_batches = consolidate_by_owner(summaries, owner_map)

        org_inspector_report = generate_inspector_report(inspector_findings)
        org_cspm_report = generate_cspm_report(cspm_findings)
        trend_chart = generate_findings_trend_chart(s3_snapshots)
        compliance_chart = generate_compliance_trend_chart(
            [{"snapshot_date": s.get("snapshot_date"), "compliance_score": 0} for s in s3_snapshots]
        )

        mail_client = GraphMailClient()
        emails_sent = 0
        for owner_email, batch in owner_batches.items():
            if owner_email == UNASSIGNED_OWNER_EMAIL:
                logger.warning("unassigned_accounts_skipped", count=len(batch["accounts"]))
                continue

            owner_reports_inspector = generate_inspector_report(
                [f for f in inspector_findings if f.get("account_id") in {a["account_id"] for a in batch["accounts"]}]
            )
            owner_reports_cspm = generate_cspm_report(
                [f for f in cspm_findings if f.get("account_id") in {a["account_id"] for a in batch["accounts"]}]
            )

            html = build_owner_email_html(
                batch["owner_name"],
                batch["accounts"],
                batch["inspector_summary"],
                batch["cspm_summary"],
            )
            await mail_client.send_mail(
                to_email=owner_email,
                subject=f"AWS Security Report — {batch['owner_name']}",
                html_body=html,
                attachments=[owner_reports_inspector, owner_reports_cspm, trend_chart, compliance_chart],
            )
            emails_sent += 1

        job.status = JobStatus.COMPLETED.value
        job.completed_at = datetime.now(timezone.utc)
        job.accounts_processed = len(accounts)
        job.findings_ingested = len(inspector_findings) + len(cspm_findings)
        job.emails_sent = emails_sent
        job.metadata_json = json.dumps(
            {
                "inspector_count": len(inspector_findings),
                "cspm_count": len(cspm_findings),
                "s3_snapshots": len(s3_snapshots),
            }
        )
        logger.info("pipeline_completed", job_id=job.id, emails=emails_sent)
    except Exception as exc:
        job.status = JobStatus.FAILED.value
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = str(exc)
        logger.exception("pipeline_failed", job_id=job.id)
        raise

    await session.flush()
    return job
