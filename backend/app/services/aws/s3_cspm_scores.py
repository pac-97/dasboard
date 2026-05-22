"""Fetch CSPM benchmark scores from S3."""

from datetime import datetime, timezone
from io import StringIO

import boto3
import pandas as pd
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_cspm_scores_from_s3(month: str | None = None) -> dict[str, dict]:
    """
    Fetch CSPM benchmark scores from S3.
    
    Args:
        month: Month in format 'May', 'June', etc. Defaults to current month.
    
    Returns:
        Dict mapping account_id to {cis: %, nist: %, cis_pass: int, nist_pass: int, ...}
    """
    if not month:
        month = datetime.now(timezone.utc).strftime("%B")
    
    settings = get_settings()
    bucket = settings.s3_findings_bucket
    
    if not bucket:
        logger.warning("s3_cspm_scores_bucket_not_configured")
        return {}
    
    key = f"all-ac-security-scores/{month}_benchmark_scores.csv"
    
    try:
        s3 = boto3.client("s3", region_name=settings.aws_region)
        response = s3.get_object(Bucket=bucket, Key=key)
        csv_content = response["Body"].read().decode("utf-8")
        
        df = pd.read_csv(StringIO(csv_content))
        logger.info("cspm_scores_loaded_from_s3", month=month, rows=len(df))
        
        # Parse CSV and normalize to dict
        # Expected columns: account_id, cis_score, nist_score, cis_pass, cis_fail, nist_pass, nist_fail
        scores = {}
        for _, row in df.iterrows():
            account_id = str(row.get("account_id", row.get("Account", ""))).strip()
            if not account_id:
                continue
            
            scores[account_id] = {
                "cis_score": float(row.get("cis_score", row.get("CIS", 0)) or 0),
                "nist_score": float(row.get("nist_score", row.get("NIST", 0)) or 0),
                "cis_pass": int(row.get("cis_pass", row.get("CIS_PASS", 0)) or 0),
                "cis_fail": int(row.get("cis_fail", row.get("CIS_FAIL", 0)) or 0),
                "nist_pass": int(row.get("nist_pass", row.get("NIST_PASS", 0)) or 0),
                "nist_fail": int(row.get("nist_fail", row.get("NIST_FAIL", 0)) or 0),
            }
        
        return scores
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        logger.error("cspm_scores_s3_fetch_error", month=month, error_code=error_code)
        return {}
    except Exception as e:
        logger.error("cspm_scores_parse_error", month=month, error=str(e))
        return {}
