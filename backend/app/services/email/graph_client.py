import base64
from pathlib import Path
from typing import Any

import httpx
import msal

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphMailClient:
    def __init__(self):
        self.settings = get_settings()
        self._token: str | None = None

    def _acquire_token(self) -> str:
        if self._token:
            return self._token

        if not self.settings.azure_client_id or not self.settings.azure_client_secret:
            raise RuntimeError("Azure AD mail credentials are not configured")

        app = msal.ConfidentialClientApplication(
            self.settings.azure_client_id,
            authority=f"https://login.microsoftonline.com/{self.settings.azure_tenant_id}",
            client_credential=self.settings.azure_client_secret,
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in result:
            raise RuntimeError(f"Failed to acquire Graph token: {result.get('error_description')}")
        self._token = result["access_token"]
        return self._token

    async def send_mail(
        self,
        to_emails: list[str],
        subject: str,
        html_body: str,
        cc_emails: list[str] | None = None,
        attachments: list[str] | None = None,
    ) -> dict[str, Any]:
        token = self._acquire_token()
        message: dict[str, Any] = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html_body},
                "toRecipients": [{"emailAddress": {"address": e}} for e in to_emails if e],
            },
            "saveToSentItems": True,
        }

        if cc_emails:
            message["message"]["ccRecipients"] = [{"emailAddress": {"address": e}} for e in cc_emails if e]

        if attachments:
            message["message"]["attachments"] = [
                self._encode_attachment(path) for path in attachments if Path(path).exists()
            ]

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{GRAPH_BASE}/users/{self.settings.mail_from_address}/sendMail",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=message,
            )
            if response.status_code not in (200, 202):
                logger.error("graph_send_failed", status=response.status_code, body=response.text)
                raise RuntimeError(f"Graph sendMail failed: {response.status_code} {response.text}")

        logger.info("email_sent", recipients=to_emails, subject=subject)
        return {"status": "sent", "recipients": to_emails}

    def _encode_attachment(self, path: str) -> dict:
        file_path = Path(path)
        content = base64.b64encode(file_path.read_bytes()).decode("utf-8")
        content_types = {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".png": "image/png",
        }
        return {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": file_path.name,
            "contentType": content_types.get(file_path.suffix.lower(), "application/octet-stream"),
            "contentBytes": content,
        }
