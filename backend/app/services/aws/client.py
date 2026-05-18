import boto3
from botocore.config import Config

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

BOTO_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"}, max_pool_connections=50)


def get_session():
    settings = get_settings()
    return boto3.Session(region_name=settings.aws_region)


def get_assumed_session():
    """Get session by assuming role in delegated admin account."""
    settings = get_settings()
    if not settings.delegated_admin_role_arn:
        logger.warning("delegated_admin_role_arn not configured, using default session")
        return get_session()
    
    try:
        sts = get_session().client("sts", region_name=settings.aws_region, config=BOTO_CONFIG)
        response = sts.assume_role(
            RoleArn=settings.delegated_admin_role_arn,
            RoleSessionName="aws-security-dashboard",
            DurationSeconds=3600,
        )
        creds = response["Credentials"]
        return boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=settings.aws_region,
        )
    except Exception as exc:
        logger.error("failed_to_assume_role", error=str(exc), role_arn=settings.delegated_admin_role_arn)
        raise


def get_client(service: str, region: str | None = None, assume_role: bool = False):
    settings = get_settings()
    session = get_assumed_session() if assume_role else get_session()
    return session.client(service, region_name=region or settings.aws_region, config=BOTO_CONFIG)
