from botocore.exceptions import ClientError

from app.core.logging import get_logger
from app.services.aws.client import get_client

logger = get_logger(__name__)


def list_organization_accounts() -> list[dict]:
    """List active organization accounts, or fall back to the current account."""
    org = get_client("organizations")
    accounts: list[dict] = []
    try:
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
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code not in {
            "AccessDeniedException",
            "AWSOrganizationsNotInUseException",
            "AccessDenied",
            "UnauthorizedOperation",
        }:
            raise

        logger.warning("organization_accounts_unavailable_falling_back_to_current_account", error=error_code)
        sts = get_client("sts")
        identity = sts.get_caller_identity()
        account_id = identity["Account"]
        return [{"account_id": account_id, "account_name": account_id, "email": None}]
