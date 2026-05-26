# CSPM, CIS & NIST Control Calculation System - Complete Overview

## Architecture Summary

This dashboard implements a comprehensive Cloud Security Posture Management (CSPM) system that tracks and reports on two compliance frameworks:
- **CIS AWS Foundations Benchmark v5.0.0** - Center for Internet Security best practices
- **NIST Special Publication 800-53 Revision 5** - National Institute of Standards & Technology security controls

---

## 1. NIST Control Calculations

### 1.1 Data Source
**Primary Source:** AWS Security Hub (Security & Compliance module)
- **File:** [backend/app/services/aws/security_hub.py](backend/app/services/aws/security_hub.py)
- **Region:** Configurable via `SECURITY_HUB_REGION` (default: ap-south-1)

### 1.2 Control Detection Algorithm
Function: `_detect_benchmark()` - Lines 40-95 in [security_hub.py](backend/app/services/aws/security_hub.py)

**Priority-based detection (5 strategies):**
1. **GeneratorId** - Extract from finding's GeneratorId field (e.g., `nist-800-53/v/5.0.0/SI-2`)
2. **AssociatedStandards** - Check `Compliance.AssociatedStandards[].StandardsId`
3. **Standards Array** - Legacy compatibility check on `Compliance.Standards[]`
4. **RelatedRequirements** - Parse `Compliance.RelatedRequirements[]` array
5. **String Matching** - Last resort JSON-wide search for "nist" or "800-53" keywords

**Constants:**
```python
NIST_BENCHMARK = "nist-800-53"
CIS_BENCHMARK = "cis-aws-foundations-benchmark"
```

### 1.3 NIST Compliance Status Classification

**Compliance Status Values:**
- `PASSED` - Control is compliant (passed)
- `FAILED` / `WARNING` - Control is non-compliant (failed)

**Calculation Logic:**
```python
# From account_cspm_scores() - Line 202-230 in security_hub.py
for finding in findings:
    benchmark = finding.get("benchmark")
    status = finding.get("compliance_status").upper()
    
    if "nist-800-53" in benchmark:
        nist_total += 1
        if status == "PASSED":
            nist_compliant += 1
        elif status in ("FAILED", "WARNING"):
            nist_failed += 1

nist_score = (nist_compliant / nist_total * 100) if nist_total > 0 else 0.0
nist_fail_count = nist_total - nist_compliant
```

**Fields Extracted:**
- `control_id` - From `Compliance.SecurityControlId` or `RelatedRequirements[0]`
- `title` - Finding title
- `description` - Full description
- `severity` - INFORMATIONAL/LOW/MEDIUM/HIGH/CRITICAL
- `resource_id` - AWS resource ARN
- `region` - AWS region
- `remediation_url` - Remediation guidance link

### 1.4 NIST Score Aggregation
**File:** [backend/app/services/aws/s3_cspm_scores.py](backend/app/services/aws/s3_cspm_scores.py) - Lines 275-310

```python
# Calculate NIST score per account
nist_score = (nist_compliant / nist_total * 100) if nist_total > 0 else 0.0

# Return breakdown
{
    "nist_score": float,        # Percentage 0-100
    "nist_pass": int,           # Count of passed controls
    "nist_fail": int            # Count of failed controls
}
```

---

## 2. CIS Control Calculations

### 2.1 Data Source
**Primary Source:** AWS Security Hub (Security & Compliance module)
- Same source as NIST
- File: [backend/app/services/aws/security_hub.py](backend/app/services/aws/security_hub.py)

### 2.2 Control Detection Algorithm
Same `_detect_benchmark()` function as NIST
- Looks for: `"cis-aws-foundations-benchmark"` in any field

### 2.3 CIS Compliance Status Classification
**Compliance Status Values:**
- `PASSED` - Control is compliant
- `FAILED` / `WARNING` - Control is non-compliant

**Calculation Logic:**
```python
# From account_cspm_scores() - Line 202-230 in security_hub.py
for finding in findings:
    benchmark = finding.get("benchmark")
    status = finding.get("compliance_status").upper()
    
    if "cis-aws-foundations-benchmark" in benchmark:
        cis_total += 1
        if status == "PASSED":
            cis_compliant += 1
        elif status in ("FAILED", "WARNING"):
            cis_failed += 1

cis_score = (cis_compliant / cis_total * 100) if cis_total > 0 else 0.0
cis_fail_count = cis_total - cis_compliant
```

**Fields Extracted:**
- `control_id` - CIS control identifier (e.g., "5.3")
- `title` - Control title
- `description` - Full description
- `severity` - INFORMATIONAL/LOW/MEDIUM/HIGH/CRITICAL
- `resource_type` - Service type (IAM, EC2, S3, etc.)
- `resource_id` - Specific resource identifier
- `region` - AWS region

### 2.4 CIS Score Aggregation
**File:** [backend/app/services/aws/s3_cspm_scores.py](backend/app/services/aws/s3_cspm_scores.py)

```python
# Calculate CIS score per account
cis_score = (cis_compliant / cis_total * 100) if cis_total > 0 else 0.0

# Return breakdown
{
    "cis_score": float,         # Percentage 0-100
    "cis_pass": int,            # Count of passed controls
    "cis_fail": int             # Count of failed controls
}
```

### 2.5 CIS vs NIST Composite Score
**File:** [backend/app/api/routes/dashboard.py](backend/app/api/routes/dashboard.py) - Line 41

```python
# Calculate composite CSPM score (average of CIS and NIST)
cspm_score = (cis_score + nist_score) / 2
```

---

## 3. Data Sources

### 3.1 AWS Inspector v2 (Vulnerability Findings)
**File:** [backend/app/services/aws/inspector.py](backend/app/services/aws/inspector.py)

**Function:** `fetch_inspector_findings()`
- **API:** `inspector2:ListFindings` via boto3
- **Region:** Configurable via `INSPECTOR_AGGREGATION_REGION`
- **Data Retrieved:**
  - CVE IDs
  - Severity levels (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL)
  - Fix availability status
  - Resource type and ID
  - EPSS score (0-10 scale)

**Severity Calculation from EPSS Score:**
```python
epss_score = finding.get("epssScore", 0)
if epss_score >= 9:
    severity = "CRITICAL"
elif epss_score >= 7:
    severity = "HIGH"
elif epss_score >= 4:
    severity = "MEDIUM"
else:
    severity = "LOW"
```

**Coverage Data:**
- Retrieved via `batch_get_account_status()`
- Coverage percentage per account (ec2 coverage %)

### 3.2 AWS Security Hub (Compliance Findings)
**File:** [backend/app/services/aws/security_hub.py](backend/app/services/aws/security_hub.py)

**Function:** `fetch_cspm_findings()`
- **API:** `securityhub:GetFindings`
- **Region:** Configurable via `SECURITY_HUB_REGION`
- **Filters Applied:**
  - `RecordState == ACTIVE`
  - `WorkflowStatus IN [NEW, NOTIFIED]`
  - Optional: Specific AWS account IDs

**Data Retrieved:**
- Benchmark classification (CIS / NIST)
- Control ID
- Compliance status (PASSED, FAILED, WARNING)
- Severity (INFORMATIONAL through CRITICAL)
- Resource details (type, ID, region)
- Remediation guidance

### 3.3 S3 CSPM Scores (Pre-calculated)
**File:** [backend/app/services/aws/s3_cspm_scores.py](backend/app/services/aws/s3_cspm_scores.py)

**Priority Order:**
1. **Direct S3 URL** - From config `CSPM_SCORES_S3_URL`
   - Example: `s3://bucket/all-ac-security-scores/May_benchmark_scores.csv`

2. **Month-based S3 path** - Auto-fetch from standard location
   - Pattern: `all-ac-security-scores/{Month}_benchmark_scores.csv`
   - Defaults to current month if not specified

3. **CSV Fields Expected:**
   - `account_id` - AWS account ID
   - `cis_score`, `cis_pass`, `cis_fail` - CIS benchmark data
   - `nist_score`, `nist_pass`, `nist_fail` - NIST benchmark data

4. **Live Data Fallback** - If S3 scores missing pass/fail counts
   - Calls `fetch_account_cspm_findings()` for each account
   - Calculates scores from live Security Hub findings
   - Caches results for 5 minutes

### 3.4 Live CSPM Findings
**File:** [backend/app/services/aws/live_data.py](backend/app/services/aws/live_data.py)

**Function:** `fetch_account_cspm_findings()`
- Fetches Security Hub findings on-demand for specific account
- Calculates `cis_pass`, `cis_fail`, `nist_pass`, `nist_fail` counts
- Returns stats in this structure:
```python
{
    "account_id": str,
    "account_name": str,
    "findings": list,
    "stats": {
        "cis_pass": int,
        "cis_fail": int,
        "nist_pass": int,
        "nist_fail": int
    },
    "status": "completed" | "failed",
    "fetched_at": timestamp
}
```

---

## 4. Excel/XLSX Report Generation

### 4.1 CSPM Report Generator
**File:** [backend/app/services/reports/inspector_cspm_reports.py](backend/app/services/reports/inspector_cspm_reports.py)

**Function:** `generate_cspm_report()` - Lines 232-403

**Creates 5 Worksheets:**

#### Sheet 1: Executive Summary
- Report date and timestamp
- Total selected accounts
- Findings breakdown:
  - Total findings count
  - Critical findings count
  - High findings count
  - Medium findings count
- Account metrics table:
  - Account ID & Name
  - CIS Score (%)
  - NIST Score (%)
  - Failed findings count

#### Sheet 2: All Failed Findings
- All non-compliant findings across severity levels
- Column headers: Account, Benchmark, Control ID, Control Title, Severity, Compliance Status, Resource ID, Region, Description, Remediation URL

#### Sheet 3: Critical Findings
- Filtered to CRITICAL severity only
- Same columns as Sheet 2
- Color-coded red background (#7F1D1D)

#### Sheet 4: High Findings
- Filtered to HIGH severity
- Color-coded orange background (#7C2D12)

#### Sheet 5: Medium Findings
- Filtered to MEDIUM severity
- Color-coded amber background (#854D0E)

**Input Parameters:**
```python
{
    "account_scores": {
        "account_id": {
            "account_name": str,
            "cis_score": float,
            "nist_score": float,
            "cis_fail": int,
            "nist_fail": int
        }
    },
    "findings_data": [
        {
            "account_id": str,
            "severity": str,
            "compliance_status": str,
            "benchmark": str,
            "control_id": str,
            "title": str,
            "description": str,
            "resource_id": str,
            "region": str,
            ...
        }
    ]
}
```

**Formatting:**
- Headers: Dark blue background (#1E293B), white text
- Data cells: Left-aligned, text wrapping enabled
- Severity columns: Color-coded based on severity
- Column widths: Auto-adjusted for readability
- Auto-filter enabled on all data rows

### 4.2 Legacy CSPM Report
**File:** [backend/app/services/reports/cspm_report.py](backend/app/services/reports/cspm_report.py)

**Creates 5 Worksheets:**
1. **Compliance Summary** - Overall CIS/NIST pass/fail counts and percentages
2. **CIS Controls** - All CIS controls with status
3. **NIST Controls** - All NIST controls with status
4. **Failed Controls** - Only failed controls
5. **Service Failures** - Breakdown by service type

### 4.3 Inspector Report Generator
**File:** [backend/app/services/reports/inspector_report.py](backend/app/services/reports/inspector_report.py)

**Creates Worksheets:**
1. **Executive Summary** - Total findings by severity
2. **Critical & High** - Critical and high severity findings
3. **All Findings** - All findings with pagination
4. **Region Breakdown** - Findings grouped by AWS region
5. **Aging Analysis** - Finding age analysis

### 4.4 Combined Inspector + CSPM Report
**File:** [backend/app/services/reports/combined_report.py](backend/app/services/reports/combined_report.py)

**Creates Worksheets:**
1. **Summary** - Executive metrics for both Inspector and CSPM
2. **Inspector Findings** - Vulnerability data
3. **CSPM Findings** - Compliance data

**Output Location:** `{reports_output_dir}/` (configurable)

---

## 5. Email Report Generation

### 5.1 CSPM Email Template
**File:** [backend/app/services/email/email_templates.py](backend/app/services/email/email_templates.py)

**Function:** `get_cspm_email_template()` - Lines 124-303

**Email Content Sections:**

#### Header
- Title: "CSPM Compliance Report"
- Subtitle: "Cloud Security Posture Management Assessment"

#### Overall Security Posture
- Gauge chart visualization
- Overall CSPM Security Score (0-100)
  - Green (#10B981) if >= 70%
  - Yellow (#F59E0B) if >= 50%
  - Red (#EF4444) if < 50%

#### Key Metrics
- Total Accounts
- CIS AWS Foundations Benchmark v5.0.0 - Average score
- NIST Special Publication 800-53 Revision 5 - Average score

#### Consolidated Account Compliance
- Visual compliance bars for each account
- CIS and NIST scores displayed side-by-side

#### Benchmark Compliance Summary Table
**Columns:**
- Account Number
- Account Name
- CIS AWS v5.0.0 % (blue text)
- CIS Fail (red text)
- NIST 800-53 R5 % (green text)
- NIST Fail (red text)

**Row Data:** All selected accounts sorted by account ID

#### What's Included Section
- Lists report contents
- Describes CIS AWS Foundations Benchmark v5.0.0
- Describes NIST Special Publication 800-53 Revision 5
- Notes about attached XLSX details

### 5.2 Inspector Email Template
**File:** [backend/app/services/email/email_templates.py](backend/app/services/email/email_templates.py)

**Function:** `get_inspector_email_template()` - Lines 1-122

**Email Content:**
- Finding summary by severity (CRITICAL, HIGH, MEDIUM)
- Account-level breakdown
- Coverage statistics
- Remediation recommendations

### 5.3 Owner/Consolidated Email Template
**File:** [backend/app/services/email/templates.py](backend/app/services/email/templates.py)

**Function:** `build_owner_email_html()` - Lines 20-110

**Email Content:**
- Header with owner name and date
- Scorecard metrics:
  - CRITICAL findings count (red)
  - HIGH findings count (orange)
  - CIS compliance % (green)
  - NIST compliance % (blue)
- Account table with:
  - Account name
  - CRITICAL count
  - HIGH count
  - CIS Score %
  - NIST Score %
- Reports attached: Inspector + CSPM XLSX files

### 5.4 Email Sending Flow
**File:** [backend/app/api/routes/email_send.py](backend/app/api/routes/email_send.py)

**Endpoint:** `POST /api/email/send`

**Payload Structure:**
```python
{
    "type": "cspm" | "inspector" | "combined",
    "account_ids": ["123456789", "987654321"],
    "to_emails": ["recipient@company.com"],
    "cc_emails": ["cc@company.com"],
    "subject": "AWS Security Report",
    "body_html": "<html>...</html>"  # Optional, auto-generated if omitted
}
```

**Process Flow (CSPM):**

1. **Fetch S3 Scores** → Get CIS/NIST scores for all accounts
2. **Calculate Overall CSPM Score** → Average of all account scores
3. **Fetch Live Findings** → For each account in parallel:
   - Call `fetch_account_cspm_findings(account_id, account_name)`
   - Extract findings status and stats
4. **Filter Findings** → Keep only:
   - Status: FAILED / FAIL / NON_COMPLIANT
   - Severity: CRITICAL / HIGH / MEDIUM
5. **Build Account Scores Dict:**
   ```python
   {
       "account_id": {
           "account_name": str,
           "cis_score": float,
           "nist_score": float,
           "cis_pass": int,
           "cis_fail": int,
           "nist_pass": int,
           "nist_fail": int
       }
   }
   ```
6. **Generate XLSX Report** → Call `generate_cspm_report(account_scores, findings_data)`
7. **Generate Email HTML** → Call `get_cspm_email_template(account_scores, cspm_security_score)`
8. **Send Email** → Via Microsoft Graph API with XLSX attachment

**Email Service:** Microsoft Graph API (Azure AD)
- **File:** [backend/app/services/email/graph_client.py](backend/app/services/email/graph_client.py)
- **Config:** Azure tenant ID, client ID, client secret
- **From Address:** Configurable via `MAIL_FROM_ADDRESS`

---

## 6. Key Functions & Files Reference

### 6.1 Core Calculation Functions

| Function | File | Purpose |
|----------|------|---------|
| `fetch_cspm_findings()` | security_hub.py | Fetch all compliance findings from Security Hub |
| `_detect_benchmark()` | security_hub.py | Classify findings as CIS or NIST |
| `account_cspm_scores()` | security_hub.py | Calculate per-account CIS/NIST scores |
| `fetch_account_cspm_findings()` | live_data.py | On-demand findings fetch with stats |
| `get_cspm_scores_from_s3()` | s3_cspm_scores.py | Fetch pre-calculated scores from S3 with fallback |
| `_enrich_scores_with_live_counts()` | s3_cspm_scores.py | Fill in missing pass/fail counts from live data |

### 6.2 Report Generation Functions

| Function | File | Purpose |
|----------|------|---------|
| `generate_cspm_report()` | inspector_cspm_reports.py | Create 5-sheet CSPM XLSX report |
| `generate_cspm_report()` | cspm_report.py | Legacy CSPM report (5 sheets) |
| `generate_inspector_report()` | inspector_report.py | Create Inspector vulnerability report |
| `generate_combined_account_report()` | combined_report.py | Create combined Inspector + CSPM report |

### 6.3 Email Template Functions

| Function | File | Purpose |
|----------|------|---------|
| `get_cspm_email_template()` | email_templates.py | Generate CSPM compliance HTML email |
| `get_inspector_email_template()` | email_templates.py | Generate Inspector findings HTML email |
| `build_owner_email_html()` | templates.py | Generate owner-consolidated email |

### 6.4 Email Sending

| Function | File | Purpose |
|----------|------|---------|
| `send_mail()` | graph_client.py | Send email via Microsoft Graph API |
| `send_email()` | email_send.py | API endpoint for sending reports |

---

## 7. Configuration Parameters

**File:** [backend/app/core/config.py](backend/app/core/config.py)

```python
# AWS Configuration
INSPECTOR_AGGREGATION_REGION = "us-east-1"      # Inspector v2 aggregation region
SECURITY_HUB_REGION = "ap-south-1"              # Security Hub region
MAX_INSPECTOR_RESULTS = 50000                    # Max findings per query

# S3 CSPM Scores
S3_FINDINGS_BUCKET = ""                          # Bucket with findings count data
S3_FINDINGS_PREFIX = "findings-count/"           # Findings count prefix
CSPM_SCORES_S3_URL = ""                          # Direct S3 path to scores CSV

# Reports
REPORTS_OUTPUT_DIR = "/reports"                  # XLSX output directory

# Email
AZURE_TENANT_ID = ""                             # Azure AD tenant
AZURE_CLIENT_ID = ""                             # App registration ID
AZURE_CLIENT_SECRET = ""                         # App registration secret
MAIL_FROM_ADDRESS = ""                           # Sender email address
MAIL_FROM_NAME = "AWS Security Dashboard"        # Sender display name
```

---

## 8. Database Tracking

**File:** [backend/app/models/email.py](backend/app/models/email.py)

**EmailDeliveryLog Table:**
- Tracks all email sends
- Fields:
  - `recipient_email` - To/CC recipients
  - `report_type` - "CSPM" or "Inspector"
  - `status` - "sent" or "failed"
  - `error_message` - If failed
  - `sent_month` - YYYY-MM format
  - `created_at` - Timestamp

---

## 9. Control Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ API Request: POST /api/email/send                           │
│ Payload: {type: "cspm", account_ids: [...]}                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        v                             v
    CSPM FLOW                   INSPECTOR FLOW
    ───────────                 ───────────────
    
    1. Fetch S3 Scores          1. Fetch Inspector findings
       (or fallback to live)       from inspector2 API
    
    2. Fetch Live CSPM          2. Aggregate by account
       Findings (parallel)          & severity
    
    3. Calculate account        3. Calculate coverage %
       CIS/NIST scores
    
    4. Filter findings          4. Generate Inspector
       (FAILED + CRITICAL/           XLSX report
       HIGH/MEDIUM)
    
    5. Generate CSPM            5. Generate Inspector
       XLSX report                  email template
    
    6. Generate CSPM            6. Send email
       email template               + attachment
    
    7. Send email
       + attachment
    
    8. Log to DB
```

---

## 10. Data Flow Example

### Example: CSPM Email Generation for 2 Accounts

**Input:**
```
POST /api/email/send
{
    "type": "cspm",
    "account_ids": ["123456789", "987654321"],
    "to_emails": ["team@company.com"]
}
```

**Step 1: Get S3 Scores**
```
S3: s3://bucket/all-ac-security-scores/May_benchmark_scores.csv
Result: {
    "123456789": {
        "cis_score": 85.5,
        "nist_score": 78.2,
        "cis_pass": 125,
        "cis_fail": 23,
        "nist_pass": 98,
        "nist_fail": 28
    },
    "987654321": {
        "cis_score": 72.1,
        "nist_score": 65.8,
        "cis_pass": 105,
        "cis_fail": 43,
        "nist_pass": 82,
        "nist_fail": 44
    }
}
```

**Step 2: Fetch Live Findings (Parallel)**
```
Security Hub API:
- Account 123456789: 51 findings (23 CIS failed, 28 NIST failed)
- Account 987654321: 87 findings (43 CIS failed, 44 NIST failed)
```

**Step 3: Filter Findings**
```
Keep only: FAILED status AND (CRITICAL OR HIGH OR MEDIUM severity)
Account 123456789: 45 actionable findings
Account 987654321: 78 actionable findings
Total: 123 findings for report
```

**Step 4: Generate XLSX**
```
Output: cspm_report_20240526_143022.xlsx
Sheets:
  1. Executive Summary - Account metrics & severity breakdown
  2. All Failed Findings - All 123 findings
  3. Critical Findings - 28 findings
  4. High Findings - 54 findings
  5. Medium Findings - 41 findings
```

**Step 5: Email Template**
```
HTML Email:
- CSPM Security Score: (85.5 + 78.2 + 72.1 + 65.8) / 4 = 75.4%
- Account Table:
  | Account    | CIS Score | CIS Fail | NIST Score | NIST Fail |
  |------------|-----------|----------|------------|-----------|
  | 123456789  | 85.5%     | 23       | 78.2%      | 28        |
  | 987654321  | 72.1%     | 43       | 65.8%      | 44        |
```

**Step 6: Send Email**
```
To: team@company.com
Subject: AWS Security Report
Attachments: cspm_report_20240526_143022.xlsx
Logged: EmailDeliveryLog with status "sent"
```

---

## 11. Error Handling & Retries

### 11.1 Security Hub API Retries
**File:** [backend/app/services/aws/security_hub.py](backend/app/services/aws/security_hub.py) - Lines 28-34

**Transient Errors (with exponential backoff):**
- ThrottlingException
- RequestLimitExceeded
- ServiceUnavailable
- InternalError
- TooManyRequestsException

**Retry Strategy:** 3 attempts with exponential backoff (2-30 seconds)

### 11.2 Live Data Fallback
If S3 data unavailable or incomplete:
1. Check if pass/fail counts are zero
2. Fetch from live Security Hub findings
3. Calculate scores dynamically
4. Cache for 5 minutes

### 11.3 Email Sending
- Logs all errors to EmailDeliveryLog table
- Returns error message in API response
- Continues even if one account fails

---

## 12. Known Limitations & Notes

1. **Live Data Performance**
   - Security Hub API calls can be slow for large account bases
   - 20-second timeout on S3 fetch, falls back to live calculation
   - Results cached for 5 minutes to reduce repeated calls

2. **Compliance Status Mapping**
   - Treats "WARNING" as "FAILED" for compliance calculation
   - Some findings may have non-standard status values

3. **Severity Classification**
   - Inspector uses EPSS score for severity calculation
   - Security Hub uses direct Severity label
   - Mapping may vary between services

4. **Region Handling**
   - Security Hub must be enabled in specified region
   - Inspector aggregation uses delegated admin account
   - Cross-region findings supported via aggregation

5. **S3 Score CSV Format**
   - Expects columns with flexible naming (case-insensitive):
     - cis_score / cis / cis_percent / cis%
     - nist_score / nist / nist_percent / nist%
     - Similar for pass/fail counts
   - Auto-detects column names

---

## 13. Related API Endpoints

**Dashboard Summary:**
- `GET /api/dashboard/executive` - Overall metrics with CSPM scores
- `GET /api/dashboard/cspm/scores` - All account CSPM scores
- `GET /api/dashboard/cspm-summary` - CIS/NIST compliance averages

**Report Email:**
- `POST /api/email/send` - Send formatted report email
- `GET /api/email/logs` - View email delivery history

**Findings:**
- `GET /api/findings/cspm` - List CSPM findings
- `GET /api/findings/inspector` - List Inspector findings

---

## Summary Table

| Component | Data Source | Calculation | Report Type | Email Type |
|-----------|-------------|-------------|------------|-----------|
| **CIS Score** | Security Hub | Pass/Total × 100 | XLSX (5 sheets) | HTML + XLSX |
| **NIST Score** | Security Hub | Pass/Total × 100 | XLSX (5 sheets) | HTML + XLSX |
| **Inspector** | Inspector v2 | Count by severity | XLSX (5 sheets) | HTML + XLSX |
| **Combined** | Both | Aggregated | XLSX (3 sheets) | HTML + XLSX |

