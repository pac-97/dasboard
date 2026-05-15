# AWS Security Dashboard

Enterprise AWS Security Dashboard with **live** Inspector and CSPM data from your delegated administrator account, per-account email reports, and owner consolidation.

## Single Docker Image (EC2)

Build and run one container on EC2 where **AWS CLI credentials** (instance profile or mounted `~/.aws`) are configured for the CSPM/Inspector delegated account:

```bash
docker build -t aws-security-dashboard .
docker run -d \
  --name security-dashboard \
  -p 8080:8080 \
  -v /home/ec2-user/.aws:/root/.aws:ro \
  -v security-dashboard-data:/data \
  -e AWS_REGION=us-east-1 \
  -e AZURE_TENANT_ID=your-tenant \
  -e AZURE_CLIENT_ID=your-app-id \
  -e AZURE_CLIENT_SECRET=your-secret \
  -e MAIL_FROM_ADDRESS=security@yourdomain.com \
  aws-security-dashboard
```

Open: **http://&lt;ec2-host&gt;:8080**

API docs: **http://&lt;ec2-host&gt;:8080/api/docs**

### AWS credentials

Boto3 uses the **same credential chain as AWS CLI** on the host:

- EC2 instance profile (recommended), or
- Mount `~/.aws` into the container (`/root/.aws`)

Required access (read-only, in delegated admin account):

- `organizations:ListAccounts`
- `inspector2:ListFindings`, `inspector2:BatchGetFindings`
- `securityhub:GetFindings`

### Azure AD email

Configure Graph API app registration with `Mail.Send` application permission for automated report emails.

## Accounts & Email workflow

1. **Accounts & Email** tab loads all 82 accounts with **live** Inspector counts and CSPM scores.
2. Click **Refresh from AWS** to pull the latest findings.
3. **Send Email** on one account, or select multiple accounts and **Email N Selected** — one email with:
   - Combined XLSX (Inspector + CSPM for all selected accounts)
   - Single PNG chart with all selected accounts
4. Email dialog: **To**, **CC**, **Subject** (auto-filled with account name), **Body**, confirm, then **Email Sent**.
5. **Email Logs** tab shows history grouped **by month**.

Owner mapping: import CSV via API `POST /api/v1/owners/import` (`owner_name`, `owner_email`, `account_id`) so **To** is pre-filled and one owner receives one email for multiple accounts.

## Local development

```bash
# Backend (uses your local AWS CLI credentials)
cd backend && pip install -r requirements.txt
export DATABASE_URL=sqlite+aiosqlite:///./local.db
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Project layout

- `backend/` — FastAPI, live AWS fetch, XLSX/charts, Graph email
- `frontend/` — Next.js static UI
- `Dockerfile` — single image (UI + API on port 8080)
- `docker/entrypoint.sh` — startup script
