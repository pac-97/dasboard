from app.core.logging import get_logger
from app.services.aws.client import get_client

logger = get_logger(__name__)


def list_organization_accounts() -> list[dict]:
    """List all active accounts in the AWS Organization."""
    org = get_client("organizations")
    accounts: list[dict] = []
    paginator = org.get_paginator("list_accounts")
    for page in paginator.paginate():
        for account in page.get("Accounts", []):
            if account.get("Status") == "ACTIVE":
                accounts.append(
                    {
                        "account_id": account["Id"],
                        "account_name": account.get("Name"),
                        "email": account.get("Email"),
                    }
                )
    logger.info("organization_accounts_listed", count=len(accounts))
    return accounts
