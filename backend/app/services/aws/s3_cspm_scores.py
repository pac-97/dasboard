"""Fetch CSPM benchmark scores from S3."""

from datetime import datetime, timezone
from io import StringIO
import re

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

        # Normalize column names for flexible access (strip, lowercase, remove non-alphanum)
        df.columns = [c.strip() for c in df.columns]
        def _norm_col_name(s: str) -> str:
            return re.sub(r"[^a-z0-9]", "", s.lower() if isinstance(s, str) else "")

        norm_cols = {_norm_col_name(c): c for c in df.columns}

        def _get_cell(r, candidates, default=None):
            for key in candidates:
                nk = _norm_col_name(key)
                if nk in norm_cols:
                    val = r.get(norm_cols[nk], default)
                    if pd.isna(val):
                        return default
                    return val
            return default

        def _to_float(v):
            try:
                if v is None:
                    return 0.0
                if isinstance(v, str):
                    v = v.strip()
                    if v.endswith('%'):
                        v = v[:-1]
                    if v == '':
                        return 0.0
                return float(v)
            except Exception:
                return 0.0

        def _to_int(v):
            try:
                if v is None:
                    return 0
                if isinstance(v, str):
                    v = v.strip()
                    if v == '':
                        return 0
                return int(float(v))
            except Exception:
                return 0

        # Parse CSV and normalize to dict
        # Be flexible with header names: account_id / Account, cis_score / CIS, nist_score / NIST, etc.
        scores = {}
        for _, row in df.iterrows():
            account_id = str(_get_cell(row, ["account_id", "account", "acct"]) or "").strip()
            if not account_id:
                # try alternative columns
                continue

            cis_score = _to_float(_get_cell(row, ["cis_score", "cis", "cis_percent", "cis%", "cis_score_%", "cis_score_pct"]))
            nist_score = _to_float(_get_cell(row, ["nist_score", "nist", "nist_percent", "nist%", "nist_score_%", "nist_score_pct"]))

            cis_pass = _to_int(_get_cell(row, ["cis_pass", "cis_pass_count", "cis_passes", "cis_passed"]))
            cis_fail = _to_int(_get_cell(row, ["cis_fail", "cis_fail_count", "cis_failed"]))
            nist_pass = _to_int(_get_cell(row, ["nist_pass", "nist_pass_count", "nist_passed"]))
            nist_fail = _to_int(_get_cell(row, ["nist_fail", "nist_fail_count", "nist_failed"]))

            scores[account_id] = {
                "cis_score": cis_score,
                "nist_score": nist_score,
                "cis_pass": cis_pass,
                "cis_fail": cis_fail,
                "nist_pass": nist_pass,
                "nist_fail": nist_fail,
            }

        if not scores:
            logger.warning("cspm_scores_empty_after_parse", month=month)

        return scores
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        logger.error("cspm_scores_s3_fetch_error", month=month, error_code=error_code)
        return {}
    except Exception as e:
        logger.error("cspm_scores_parse_error", month=month, error=str(e))
        return {}
