const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API error: ${res.status}`);
  }
  return res.json();
}

export const api = {
  accountsList: (refresh = false) =>
    fetchApi<AccountsListResponse>(`/findings/accounts?refresh=${refresh}`),
  
  fetchInspectorAccount: (accountId: string) =>
    fetchApi<AccountFindingsResponse>(`/findings/inspector/fetch-account/${accountId}`, { method: "POST" }),
  
  fetchCspmAccount: (accountId: string) =>
    fetchApi<AccountFindingsResponse>(`/findings/cspm/fetch-account/${accountId}`, { method: "POST" }),

  accountsLive: (refresh = false) =>
    fetchApi<AccountsLiveResponse>(`/accounts/live?refresh=${refresh}`),
  refreshAccounts: () => fetchApi<AccountsLiveResponse>("/accounts/refresh", { method: "POST" }),

  executive: (refresh = false) => fetchApi<ExecutiveOverview>(`/dashboard/executive?refresh=${refresh}`),
  inspectorSummary: (refresh = false) =>
    fetchApi<InspectorSummary>(`/dashboard/inspector/summary?refresh=${refresh}`),
  cspmSummary: (refresh = false) => fetchApi<CspmSummary>(`/dashboard/cspm/summary?refresh=${refresh}`),
  cspmScores: (month?: string) => {
    const q = month ? `?month=${month}` : "";
    return fetchApi<CspmScoresResponse>(`/dashboard/cspm/scores${q}`);
  },

  inspectorFindings: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi<InspectorFinding[]>(`/findings/inspector?${q}`);
  },
  cspmFindings: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi<CspmFinding[]>(`/findings/cspm?${q}`);
  },

  composeEmailPreview: (accountIds: string[], findingType: string = "inspector") =>
    fetchApi<ComposePreview>("/email/compose-preview", {
      method: "POST",
      body: JSON.stringify({ account_ids: accountIds, finding_type: findingType }),
    }),

  sendEmail: (payload: SendEmailPayload) =>
    fetchApi<{ status: string; message: string; log_id: number }>("/email/send", {
      method: "POST",
      body: JSON.stringify({ ...payload, confirmed: true }),
    }),

  emailLogs: (month?: string) => {
    const q = month ? `?month=${month}` : "";
    return fetchApi<EmailLogsResponse>(`/email/logs${q}`);
  },

  owners: () => fetchApi<Owner[]>("/owners"),
  operations: () => fetchApi<OperationsOverview>("/operations/overview"),
};

export interface AccountRow {
  account_id: string;
  account_name: string;
  email?: string;
  inspector_total?: number;
  inspector_critical?: number;
  inspector_high?: number;
  inspector_medium?: number;
  inspector_low?: number;
  cspm_score?: number;
  cis_score?: number;
  nist_score?: number;
  cspm_total_findings?: number;
  cspm_failed_controls?: number;
  owner_id?: number;
  owner_name?: string;
  owner_email?: string;
}

export interface AccountsListResponse {
  fetched_at: number;
  account_count: number;
  accounts: AccountRow[];
}

export interface AccountFindingsResponse {
  account_id: string;
  account_name: string;
  findings: InspectorFinding[] | CspmFinding[];
  stats: Record<string, number>;
  fetched_at: number;
}

export interface AccountsLiveResponse {
  fetched_at: number;
  account_count: number;
  org_totals: { inspector_total: number; cspm_total: number; accounts: number };
  accounts: AccountRow[];
}

export interface ComposePreview {
  subject: string;
  body_html: string;
  suggested_to: string[];
  account_rows: AccountRow[];
}

export interface SendEmailPayload {
  account_ids: string[];
  finding_type: string;
  to_emails: string[];
  cc_emails: string[];
  subject: string;
  body_html: string;
}

export interface EmailLogsResponse {
  months: string[];
  logs_by_month: Record<string, EmailLogEntry[]>;
}

export interface EmailLogEntry {
  id: number;
  recipient: string;
  cc?: string;
  subject: string;
  status: string;
  account_ids: string[];
  sent_at: string | null;
  created_at: string | null;
  error_message: string | null;
}

export interface ExecutiveOverview {
  total_findings: number;
  critical_findings: number;
  high_findings: number;
  compliance_score: number;
  cis_score: number;
  nist_score: number;
  severity_distribution: Record<string, number>;
  top_risky_accounts: { account_id: string; account_name: string; total: number; critical: number; risk_score: number }[];
  rising_risk_accounts: { account_id: string; delta_critical: number }[];
  most_vulnerable_services: { service: string; count: number }[];
  posture_trend: { date: string; critical: number; high: number; total: number }[];
  resource_exposure: Record<string, number>;
  fetched_at?: number;
}

export interface InspectorSummary {
  severity_distribution: Record<string, number>;
  region_distribution: Record<string, number>;
  fix_availability: Record<string, number>;
  total: number;
}

export interface CspmSummary {
  cis_compliance: number;
  nist_compliance: number;
  top_failed_services: { service: string; count: number }[];
  account_comparison: { account_id: string; account_name: string; failed_controls: number }[];
}

export interface CspmScoresResponse {
  scores: {
    [account_id: string]: {
      cis_score: number;
      nist_score: number;
      cis_pass: number;
      cis_fail: number;
      nist_pass: number;
      nist_fail: number;
    };
  };
  source: "s3" | "live_data" | "none";
  error: string | null;
}

export interface InspectorFinding {
  finding_arn: string;
  account_id: string;
  title: string;
  severity: string;
  status: string;
  region: string | null;
  cve_ids: string | null;
  fix_available: boolean | null;
}

export interface CspmFinding {
  finding_id: string;
  account_id: string;
  benchmark: string;
  control_id: string;
  title: string;
  compliance_status: string;
  severity: string;
}

export interface Owner {
  id: number;
  name: string;
  email: string;
  accounts: string[];
}

export interface OperationsOverview {
  stats: Record<string, number>;
  recent_jobs: { id: number; type: string; status: string }[];
  email_logs: { recipient: string; status: string; subject: string }[];
  audit_history: { action: string; actor: string; created_at: string }[];
}
