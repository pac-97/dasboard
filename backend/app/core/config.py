from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AWS Security Dashboard"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "sqlite+aiosqlite:////data/security_dashboard.db"
    redis_url: str = "redis://localhost:6379/0"
    static_dir: str = "/app/static"

    # AWS (delegated admin account credentials on EC2 instance role or keys)
    aws_region: str = "ap-south-1"
    aws_delegated_account_id: str = ""
    aws_organization_id: str = ""
    security_hub_admin_account_id: str = ""
    delegated_admin_role_arn: str = ""
    inspector_aggregation_region: str = "ap-south-1"
    security_hub_region: str = "ap-south-1"
    max_inspector_results: int = 50000

    # S3 findings count bucket
    s3_findings_bucket: str = ""
    s3_findings_prefix: str = "findings-count/"
    
    # S3 CSPM Scores (direct URL or auto-fetch by month)
    cspm_scores_s3_url: str = ""  # Direct S3 path, e.g., s3://bucket/all-ac-security-scores/May_benchmark_scores.csv

    # Azure AD / Microsoft Graph
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    mail_from_address: str = ""
    mail_from_name: str = "AWS Security Dashboard"

    # Auth
    azure_ad_audience: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Scheduling
    scheduler_timezone: str = "UTC"
    default_schedule_cron: str = "0 6 * * 1"

    # Reports
    reports_output_dir: str = "/tmp/reports"
    charts_output_dir: str = "/tmp/charts"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
