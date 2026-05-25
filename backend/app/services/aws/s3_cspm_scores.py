"""Fetch CSPM benchmark scores from S3."""

from datetime import datetime, timezone, timedelta
from io import StringIO
import re
from typing import Optional, Dict, Any

import boto3
import pandas as pd
from botocore.exceptions import ClientError

from app.services.aws.live_data import (
    fetch_account_cspm_findings,
    get_live_snapshot,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# In-memory cache for S3 scores with TTL
_scores_cache: Dict[str, Dict[str, Any]] = {}
_cache_timestamp: Optional[datetime] = None
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _is_cis_benchmark(benchmark: str) -> bool:
    benchmark = str(benchmark).lower().strip()

    return any(
        x in benchmark
        for x in [
            "cis-aws-foundations-benchmark",
            "cis aws foundations benchmark",
            "cis",
        ]
    )


def _is_nist_benchmark(benchmark: str) -> bool:
    benchmark = str(benchmark).lower().strip()

    return any(
        x in benchmark
        for x in [
            "nist-800-53",
            "nist special publication 800-53",
            "nist",
        ]
    )


def _is_compliant(status: str) -> bool:
    status = str(status).upper().strip()
    return status in ["PASSED", "COMPLIANT"]


async def _enrich_scores_with_live_counts(scores: dict) -> dict:
    """
    Enrich S3 scores with pass/fail counts from live findings if missing.
    """

    needs_enrichment = any(
        score.get("cis_pass", 0) == 0
        and score.get("cis_fail", 0) == 0
        and score.get("nist_pass", 0) == 0
        and score.get("nist_fail", 0) == 0
        for score in scores.values()
    )

    if not needs_enrichment:
        return scores

    logger.info(
        "cspm_scores_enriching_with_live_counts",
        account_count=len(scores),
    )

    try:
        snapshot = await get_live_snapshot()
        accounts = snapshot.get("accounts", [])

        for account in accounts:
            account_id = account["account_id"]

            if account_id not in scores:
                continue

            existing = scores.get(account_id, {})

            if (
                existing.get("cis_pass", 0) > 0
                or existing.get("cis_fail", 0) > 0
                or existing.get("nist_pass", 0) > 0
                or existing.get("nist_fail", 0) > 0
            ):
                continue

            account_name = account["account_name"]

            logger.info(
                "account_cspm_fetch_start",
                account_id=account_id,
                account_name=account_name,
            )

            result = await fetch_account_cspm_findings(
                account_id,
                account_name,
            )

            if result.get("status") != "completed":
                logger.warning(
                    "cspm_scores_enrichment_failed_account",
                    account_id=account_id,
                    status=result.get("status"),
                    error=result.get("error"),
                )
                continue

            findings = result.get("findings", [])

            cis_total = 0
            cis_compliant = 0
            nist_total = 0
            nist_compliant = 0

            for finding in findings:
                benchmark = finding.get("benchmark", "")
                status = finding.get("compliance_status", "")

                if _is_cis_benchmark(benchmark):
                    cis_total += 1

                    if _is_compliant(status):
                        cis_compliant += 1

                elif _is_nist_benchmark(benchmark):
                    nist_total += 1

                    if _is_compliant(status):
                        nist_compliant += 1

            scores[account_id]["cis_pass"] = cis_compliant
            scores[account_id]["cis_fail"] = max(
                0,
                cis_total - cis_compliant,
            )

            scores[account_id]["nist_pass"] = nist_compliant
            scores[account_id]["nist_fail"] = max(
                0,
                nist_total - nist_compliant,
            )

            logger.info(
                "cspm_scores_enriched_account",
                account_id=account_id,
                cis_total=cis_total,
                cis_pass=cis_compliant,
                nist_total=nist_total,
                nist_pass=nist_compliant,
            )

    except Exception as e:
        logger.warning(
            "cspm_scores_enrichment_failed",
            error=str(e),
        )

    return scores


async def get_cspm_scores_from_s3(
    month: str | None = None,
    skip_cache: bool = False,
) -> dict:
    """
    Fetch CSPM benchmark scores from S3
    with fallback to live Security Hub findings.
    """

    global _scores_cache, _cache_timestamp

    # Cache check
    if not skip_cache and _scores_cache and _cache_timestamp:
        cache_age = (
            datetime.now(timezone.utc)
            - _cache_timestamp
        )

        if cache_age < timedelta(
            seconds=_CACHE_TTL_SECONDS
        ):
            logger.debug(
                "cspm_scores_using_cache",
                cache_age_seconds=cache_age.total_seconds(),
            )

            return {
                "scores": _scores_cache,
                "source": "cache",
                "error": None,
            }

    settings = get_settings()
    s3_error = None

    direct_url = settings.cspm_scores_s3_url
    bucket = settings.s3_findings_bucket

    logger.info(
        "cspm_scores_config",
        direct_url_configured=bool(direct_url),
        bucket_configured=bool(bucket),
    )

    # -------------------------
    # S3 FETCH
    # -------------------------
    if direct_url or bucket:
        try:
            if direct_url:
                if not direct_url.startswith("s3://"):
                    raise ValueError(
                        "Invalid CSPM_SCORES_S3_URL"
                    )

                parts = (
                    direct_url.replace("s3://", "")
                    .split("/", 1)
                )

                bucket = parts[0]
                key = parts[1]

            else:
                if not month:
                    month = datetime.now(
                        timezone.utc
                    ).strftime("%B")

                key = (
                    f"all-ac-security-scores/"
                    f"{month}_benchmark_scores.csv"
                )

            logger.info(
                "cspm_scores_fetching_from_s3",
                bucket=bucket,
                key=key,
            )

            s3 = boto3.client(
                "s3",
                region_name=settings.aws_region,
            )

            response = s3.get_object(
                Bucket=bucket,
                Key=key,
            )

            csv_content = (
                response["Body"]
                .read()
                .decode("utf-8")
            )

            df = pd.read_csv(
                StringIO(csv_content)
            )

            df.columns = [
                c.strip() for c in df.columns
            ]

            def _norm_col_name(s: str):
                return re.sub(
                    r"[^a-z0-9]",
                    "",
                    str(s).lower(),
                )

            norm_cols = {
                _norm_col_name(c): c
                for c in df.columns
            }

            def _get_cell(
                row,
                candidates,
                default=None,
            ):
                for c in candidates:
                    key_name = _norm_col_name(c)

                    if key_name in norm_cols:
                        value = row.get(
                            norm_cols[key_name],
                            default,
                        )

                        if pd.isna(value):
                            return default

                        return value

                return default

            scores = {}

            for _, row in df.iterrows():
                account_id = str(
                    _get_cell(
                        row,
                        [
                            "account_id",
                            "accountid",
                            "account",
                        ],
                        "",
                    )
                ).strip()

                if not account_id:
                    continue

                scores[account_id] = {
                    "cis_score": float(
                        _get_cell(
                            row,
                            ["cis_score"],
                            0,
                        )
                    ),
                    "nist_score": float(
                        _get_cell(
                            row,
                            ["nist_score"],
                            0,
                        )
                    ),
                    "cis_pass": int(
                        _get_cell(
                            row,
                            ["cis_pass"],
                            0,
                        )
                    ),
                    "cis_fail": int(
                        _get_cell(
                            row,
                            ["cis_fail"],
                            0,
                        )
                    ),
                    "nist_pass": int(
                        _get_cell(
                            row,
                            ["nist_pass"],
                            0,
                        )
                    ),
                    "nist_fail": int(
                        _get_cell(
                            row,
                            ["nist_fail"],
                            0,
                        )
                    ),
                }

            if scores:
                logger.info(
                    "cspm_scores_successfully_fetched_from_s3",
                    account_count=len(scores),
                )

                scores = await _enrich_scores_with_live_counts(
                    scores
                )

                _scores_cache.clear()
                _scores_cache.update(scores)

                _cache_timestamp = datetime.now(
                    timezone.utc
                )

                return {
                    "scores": scores,
                    "source": "s3",
                    "error": None,
                }

        except ClientError as e:
            s3_error = str(e)

        except Exception as e:
            s3_error = str(e)

    # -------------------------
    # FALLBACK TO LIVE DATA
    # -------------------------
    logger.info(
        "cspm_scores_attempting_fallback_to_live_data",
        s3_error=s3_error,
    )

    fallback_scores = {}

    try:
        snapshot = await get_live_snapshot()
        accounts = snapshot.get(
            "accounts",
            [],
        )

        for account in accounts:
            account_id = account[
                "account_id"
            ]
            account_name = account[
                "account_name"
            ]

            result = await fetch_account_cspm_findings(
                account_id,
                account_name,
            )

            if (
                result.get("status")
                != "completed"
            ):
                continue

            findings = result.get(
                "findings",
                [],
            )

            cis_total = 0
            cis_compliant = 0
            nist_total = 0
            nist_compliant = 0

            for finding in findings:
                benchmark = finding.get(
                    "benchmark",
                    "",
                )

                status = finding.get(
                    "compliance_status",
                    "",
                )

                if _is_cis_benchmark(
                    benchmark
                ):
                    cis_total += 1

                    if _is_compliant(
                        status
                    ):
                        cis_compliant += 1

                elif _is_nist_benchmark(
                    benchmark
                ):
                    nist_total += 1

                    if _is_compliant(
                        status
                    ):
                        nist_compliant += 1

            fallback_scores[
                account_id
            ] = {
                "cis_score": (
                    (
                        cis_compliant
                        / cis_total
                    )
                    * 100
                    if cis_total > 0
                    else 0.0
                ),
                "nist_score": (
                    (
                        nist_compliant
                        / nist_total
                    )
                    * 100
                    if nist_total > 0
                    else 0.0
                ),
                "cis_pass": cis_compliant,
                "cis_fail": max(
                    0,
                    cis_total
                    - cis_compliant,
                ),
                "nist_pass": nist_compliant,
                "nist_fail": max(
                    0,
                    nist_total
                    - nist_compliant,
                ),
            }

        if fallback_scores:
            _scores_cache.clear()
            _scores_cache.update(
                fallback_scores
            )

            _cache_timestamp = datetime.now(
                timezone.utc
            )

            return {
                "scores": fallback_scores,
                "source": "live_data",
                "error": s3_error,
            }

    except Exception as e:
        logger.error(
            "cspm_scores_fallback_calculation_error",
            error=str(e),
        )

    return {
        "scores": {},
        "source": "none",
        "error": s3_error
        or "Unable to fetch CSPM scores",
    }