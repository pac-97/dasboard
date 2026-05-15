import boto3
from botocore.config import Config

from app.core.config import get_settings

BOTO_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"}, max_pool_connections=50)


def get_session():
    settings = get_settings()
    return boto3.Session(region_name=settings.aws_region)


def get_client(service: str, region: str | None = None):
    settings = get_settings()
    session = get_session()
    return session.client(service, region_name=region or settings.aws_region, config=BOTO_CONFIG)
