"""Fetch CSPM benchmark scores from S3."""

from datetime import datetime, timezone
from io import StringIO
import re

import boto3
import pandas as pd
from botocore.exceptions import ClientError

from app.services.aws.live_data import fetch_account_cspm_findings, get_live_snapshot
from app.schemas.findings import CspmFindingOut

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_cspm_scores_from_s3(month: str | None = None) -> dict:
    """
    Fetch CSPM benchmark scores from S3, with fallback to live data calculation.
    
    Priority:
    1. Use direct CSPM_SCORES_S3_URL if configured
    2. Try to fetch from s3://bucket/all-ac-security-scores/{month}_benchmark_scores.csv
    3. Fall back to calculating from live CSPM findings
    
    Args:
        month: Month in format 'May', 'June', etc. Defaults to current month.
    
    Returns:
        {
            "scores": Dict[account_id -> {cis_score, nist_score, cis_pass, cis_fail, nist_pass, nist_fail}],
            "source": "s3" | "live_data" | "none",
            "error": str or None
        }
    """
    settings = get_settings()
    s3_error = None
    
    # Try direct URL first (if configured)
    direct_url = settings.cspm_scores_s3_url
    bucket = settings.s3_findings_bucket
    
    if not direct_url and not bucket:
        s3_error = "S3 bucket and CSPM_SCORES_S3_URL not configured"
        logger.warning("s3_cspm_scores_bucket_not_configured")
    else:
        # Determine S3 path
        if direct_url:
            # Parse direct URL: s3://bucket/path/to/file.csv
            if direct_url.startswith("s3://"):
                parts = direct_url.replace("s3://", "").split("/", 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ""
                logger.info("cspm_scores_using_direct_s3_url", url=direct_url)
            else:
                s3_error = "Invalid CSPM_SCORES_S3_URL format (must start with s3://)"
                logger.error("cspm_scores_invalid_direct_url", url=direct_url)
                key = None
        else:
            # Construct month-based path
            if not month:
                month = datetime.now(timezone.utc).strftime("%B")
            key = f"all-ac-security-scores/{month}_benchmark_scores.csv"
            logger.info("cspm_scores_using_month_based_path", month=month, key=key)
        
        if key:  # Only proceed if we have a valid key
            try:
                s3 = boto3.client("s3", region_name=settings.aws_region)
                response = s3.get_object(Bucket=bucket, Key=key)
                csv_content = response["Body"].read().decode("utf-8")
                
                df = pd.read_csv(StringIO(csv_content))
                logger.info("cspm_scores_loaded_from_s3", key=key, rows=len(df))

                # Normalize column names for flexible access (strip, lowercase, remove non-alphanum)
                df.columns = [c.strip() for c in df.columns]
                def _norm_col_name(s: str) -> str:
                    return re.sub(r"[^a-z0-9]", "", s.lower() if isinstance(s, str) else "")

                norm_cols = {_norm_col_name(c): c for c in df.columns}

                def _get_cell(r, candidates, default=None):
                    for key_candidate in candidates:
                        nk = _norm_col_name(key_candidate)
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
                scores = {}
                for _, row in df.iterrows():
                    account_id = str(_get_cell(row, ["account_id", "account", "acct", "accountid"]) or "").strip()
                    if not account_id:
                        continue

                    cis_score = _to_float(_get_cell(row, ["cis_score", "cis", "cis_percent", "cis%", "cis_score_%", "cis_score_pct", "cis-score"]))
                    nist_score = _to_float(_get_cell(row, ["nist_score", "nist", "nist_percent", "nist%", "nist_score_%", "nist_score_pct", "nist-score"]))

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

                if scores:
                    logger.info("cspm_scores_successfully_fetched_from_s3", key=key, account_count=len(scores))
                    return {"scores": scores, "source": "s3", "error": None}
                else:
                    s3_error = "No valid account records parsed from S3 CSV"
                    logger.warning("cspm_scores_empty_after_parse", key=key)

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                s3_error = f"S3 fetch failed: {error_code}"
                logger.error("cspm_scores_s3_fetch_error", key=key, error_code=error_code, s3_error=s3_error)
            except Exception as e:
                s3_error = f"S3 data parsing failed: {str(e)}"
                logger.error("cspm_scores_parse_error", key=key, error=str(e), s3_error=s3_error)
    
    # Fallback to calculating from live findings
    logger.info("cspm_scores_attempting_fallback_to_live_data", s3_error=s3_error)
    fallback_scores = {}
    
    try:
        snapshot = await get_live_snapshot()
        accounts = snapshot.get("accounts", [])

        for account in accounts:
            account_id = account["account_id"]
            account_name = account["account_name"]
            result = await fetch_account_cspm_findings(account_id, account_name)

            if result.get("status") == "completed" and result.get("findings"):
                findings = result["findings"]
                
                cis_total = 0
                cis_compliant = 0
                nist_total = 0
                nist_compliant = 0

                for finding in findings:
                    benchmark = finding.get("benchmark", "").lower()
                    status = finding.get("compliance_status", "").upper()
                    
                    if "cis aws foundations benchmark" in benchmark:
                        cis_total += 1
                        if status == "COMPLIANT":
                            cis_compliant += 1
                    elif "nist special publication 800-53" in benchmark:
                        nist_total += 1
                        if status == "COMPLIANT":
                            nist_compliant += 1

                cis_score = (cis_compliant / cis_total * 100) if cis_total > 0 else 0.0
                nist_score = (nist_compliant / nist_total * 100) if nist_total > 0 else 0.0

                fallback_scores[account_id] = {
                    "cis_score": cis_score,
                    "nist_score": nist_score,
                    "cis_pass": cis_compliant,
                    "cis_fail": cis_total - cis_compliant,
                    "nist_pass": nist_compliant,
                    "nist_fail": nist_total - nist_compliant,
                }
            else:
                logger.warning("cspm_scores_fallback_no_findings", account_id=account_id, status=result.get("status"), error=result.get("error"))

        if fallback_scores:
            logger.info("cspm_scores_fallback_calculation_success", account_count=len(fallback_scores))
            return {"scores": fallback_scores, "source": "live_data", "error": s3_error}
        
    except Exception as e:
        logger.error("cspm_scores_fallback_calculation_error", error=str(e))

    logger.error("cspm_scores_no_data_available", s3_error=s3_error)
    return {"scores": {}, "source": "none", "error": s3_error or "Unable to fetch CSPM scores from S3 or live data"}
