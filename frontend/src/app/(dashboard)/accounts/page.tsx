"use client";

import { useMemo, useState } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Mail, RefreshCw, Search, AlertCircle, Loader2 } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmailComposeDialog } from "@/components/email/email-compose-dialog";
import { api, AccountRow, CspmScoresResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

// Types for on-demand fetching
type FetchStatus = "not_fetched" | "fetching" | "completed" | "failed";
type AccountStatus = {
  inspectorStatus: FetchStatus;
  inspectorCount: number | null;
  inspectorError?: string;
  cspmStatus: FetchStatus;
  cspmCount: number | null;
  cspmError?: string;
  cisScore?: number;
  nistScore?: number;
};

export default function AccountsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [emailOpen, setEmailOpen] = useState(false);
  const [emailAccounts, setEmailAccounts] = useState<string[]>([]);
  const [tab, setTab] = useState<"inspector" | "cspm" | "logs">("inspector");
  const [logMonth, setLogMonth] = useState("");
  const [accountStatus, setAccountStatus] = useState<Record<string, AccountStatus>>({});

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ["accounts-live"],
    queryFn: () => api.accountsList(false),
    refetchOnWindowFocus: false,
  });

  const { data: cspmScores, isLoading: isLoadingCspmScores } = useQuery({
    queryKey: ["cspm-scores"],
    queryFn: () => api.cspmScores(),
    enabled: tab === "cspm",
  });

  const { data: emailLogs } = useQuery({
    queryKey: ["email-logs", logMonth],
    queryFn: () => api.emailLogs(logMonth || undefined),
    enabled: tab === "logs",
  });

  // Mutations for per-account fetching
  const inspectorMutation = useMutation({
    mutationFn: async (accountId: string) => {
      setAccountStatus((prev) => ({
        ...prev,
        [accountId]: {
          ...prev[accountId],
          inspectorStatus: "fetching",
        },
      }));
      const result = await api.fetchInspectorAccount(accountId);
      return { accountId, result };
    },
    onSuccess: ({ accountId, result }) => {
      setAccountStatus((prev) => ({
        ...prev,
        [accountId]: {
          ...prev[accountId],
          inspectorStatus: "completed",
          inspectorCount: result.findings?.length || 0,
        },
      }));
    },
    onError: (error, accountId) => {
      setAccountStatus((prev) => ({
        ...prev,
        [accountId]: {
          ...prev[accountId],
          inspectorStatus: "failed",
          inspectorError: (error as Error).message,
        },
      }));
    },
  });

  const cspmMutation = useMutation({
    mutationFn: async (accountId: string) => {
      setAccountStatus((prev) => ({
        ...prev,
        [accountId]: {
          ...prev[accountId],
          cspmStatus: "fetching",
        },
      }));
      const result = await api.fetchCspmAccount(accountId);
      return { accountId, result };
    },
    onSuccess: ({ accountId, result }) => {
      setAccountStatus((prev) => ({
        ...prev,
        [accountId]: {
          ...prev[accountId],
          cspmStatus: "completed",
          cspmCount: result.findings?.length || 0,
        },
      }));
    },
    onError: (error, accountId) => {
      setAccountStatus((prev) => ({
        ...prev,
        [accountId]: {
          ...prev[accountId],
          cspmStatus: "failed",
          cspmError: (error as Error).message,
        },
      }));
    },
  });

  const accounts = data?.accounts ?? [];
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return accounts;
    return accounts.filter(
      (a) =>
        a.account_name.toLowerCase().includes(q) ||
        a.account_id.includes(q) ||
        (a.email || "").toLowerCase().includes(q)
    );
  }, [accounts, search]);

  const fetchedLabel = data?.fetched_at
    ? new Date(data.fetched_at * 1000).toLocaleString()
    : "—";

  return (
    <div>
      <Topbar
        title="Findings & Email"
        subtitle={`Live AWS data · ${data?.account_count ?? "—"} accounts · Last refresh: ${fetchedLabel}`}
      />

      <div className="px-8 pt-4 flex gap-2 border-b border-border/50">
        <button
          onClick={() => setTab("inspector")}
          className={cn("px-4 py-2 text-sm font-medium rounded-t-lg", tab === "inspector" ? "bg-card text-primary" : "text-muted-foreground")}
        >
          Inspector Findings
        </button>
        <button
          onClick={() => setTab("cspm")}
          className={cn("px-4 py-2 text-sm font-medium rounded-t-lg", tab === "cspm" ? "bg-card text-primary" : "text-muted-foreground")}
        >
          CSPM Findings
        </button>
        <button
          onClick={() => setTab("logs")}
          className={cn("px-4 py-2 text-sm font-medium rounded-t-lg", tab === "logs" ? "bg-card text-primary" : "text-muted-foreground")}
        >
          Email Logs
        </button>
      </div>

      <div className="p-8 space-y-4">
        {(tab === "inspector" || tab === "cspm") && (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[200px] max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search account, ID, email…"
                  className="w-full rounded-lg border border-border bg-muted/30 py-2 pl-10 pr-4 text-sm"
                />
              </div>
              <button
                onClick={() => refetch()}
                disabled={isFetching}
                className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm hover:bg-muted"
              >
                <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
                Refresh Accounts
              </button>
            </div>

            {error && (
              <Card className="border-red-500/30 bg-red-500/5">
                <CardContent className="p-4 text-sm text-red-400">
                  Failed to load AWS data: {(error as Error).message}. Ensure EC2 has delegated-account AWS CLI credentials.
                </CardContent>
              </Card>
            )}

            {isLoading ? (
              <div className="text-center py-20 text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3" />
                Fetching account list…
              </div>
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle>{tab === "inspector" ? "Inspector Findings" : "CSPM Findings"}</CardTitle>
                </CardHeader>
                <CardContent className="overflow-x-auto p-0">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-muted/20 text-left text-muted-foreground">
                        <th className="p-3">Account Name</th>
                        <th className="p-3">Account ID</th>
                        <th className="p-3">Email</th>
                        {tab === "inspector" ? (
                          <>
                            <th className="p-3">Findings Count</th>
                            <th className="p-3">Status</th>
                          </>
                        ) : (
                          <>
                            <th className="p-3">CIS AWS Foundations v5.0.0</th>
                            <th className="p-3">NIST 800-53 Revision 5</th>
                            <th className="p-3">Status</th>
                          </>
                        )}
                        <th className="p-3">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((acc) => (
                        <AccountTableRow
                          key={acc.account_id}
                          acc={acc}
                          tab={tab}
                          status={
                            accountStatus[acc.account_id] || {
                              inspectorStatus: "not_fetched",
                              inspectorCount: null,
                              cspmStatus: "not_fetched",
                              cspmCount: null,
                            }
                          }
                          cspmScores={cspmScores || {}}
                          onFetchInspector={() => inspectorMutation.mutate(acc.account_id)}
                          onFetchCspm={() => cspmMutation.mutate(acc.account_id)}
                          onEmail={() => {
                            setEmailAccounts([acc.account_id]);
                            setEmailOpen(true);
                          }}
                          isLoadingInspector={inspectorMutation.isPending && inspectorMutation.variables === acc.account_id}
                          isLoadingCspm={cspmMutation.isPending && cspmMutation.variables === acc.account_id}
                        />
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {tab === "logs" && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Email Logs (month-wise)</CardTitle>
              <select
                value={logMonth}
                onChange={(e) => setLogMonth(e.target.value)}
                className="rounded-lg border border-border bg-muted/30 px-3 py-1.5 text-sm"
              >
                <option value="">All months</option>
                {(emailLogs?.months ?? []).map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.entries(emailLogs?.logs_by_month ?? {})
                .filter(([m]) => !logMonth || m === logMonth)
                .map(([month, logs]) => (
                  <div key={month}>
                    <p className="text-xs font-semibold uppercase text-muted-foreground mb-2">{month}</p>
                    {logs.map((log) => (
                      <div key={log.id} className="mb-2 rounded-lg border border-border/50 px-4 py-3 text-sm">
                        <div className="flex justify-between">
                          <span className="font-medium">{log.subject}</span>
                          <span className={log.status === "sent" ? "text-emerald-400" : "text-red-400"}>{log.status}</span>
                        </div>
                        <p className="text-muted-foreground text-xs mt-1">To: {log.recipient}</p>
                        <p className="text-muted-foreground text-xs">Accounts: {log.account_ids.join(", ")}</p>
                        {log.sent_at && <p className="text-xs text-muted-foreground mt-1">{log.sent_at}</p>}
                      </div>
                    ))}
                  </div>
                ))}
              {!emailLogs?.months?.length && <p className="text-muted-foreground text-sm">No emails sent yet.</p>}
            </CardContent>
          </Card>
        )}
      </div>

      {emailOpen && (
        <EmailComposeDialog
          accountIds={emailAccounts}
          accounts={accounts}
          onClose={() => setEmailOpen(false)}
          onSent={() => {
            qc.invalidateQueries({ queryKey: ["email-logs"] });
          }}
        />
      )}
    </div>
  );
}

function AccountTableRow({
  acc,
  tab,
  status,
  cspmScores,
  onFetchInspector,
  onFetchCspm,
  onEmail,
  isLoadingInspector,
  isLoadingCspm,
}: {
  acc: AccountRow;
  tab: "inspector" | "cspm";
  status: AccountStatus;
  cspmScores: CspmScoresResponse;
  onFetchInspector: () => void;
  onFetchCspm: () => void;
  onEmail: () => void;
  isLoadingInspector: boolean;
  isLoadingCspm: boolean;
}) {
  const currentStatus = tab === "inspector" ? status.inspectorStatus : status.cspmStatus;
  const currentCount = tab === "inspector" ? status.inspectorCount : status.cspmCount;
  const currentError = tab === "inspector" ? status.inspectorError : status.cspmError;
  const isLoading = tab === "inspector" ? isLoadingInspector : isLoadingCspm;
  const onFetch = tab === "inspector" ? onFetchInspector : onFetchCspm;

  // Get CSPM scores for this account
  const accountCspmScores = cspmScores[acc.account_id] || {
    cis_score: 0,
    nist_score: 0,
    cis_pass: 0,
    cis_fail: 0,
    nist_pass: 0,
    nist_fail: 0,
  };

  const statusColor =
    currentStatus === "not_fetched"
      ? "text-muted-foreground"
      : currentStatus === "fetching"
      ? "text-blue-400"
      : currentStatus === "completed"
      ? "text-emerald-400"
      : "text-red-400";

  const statusLabel =
    currentStatus === "not_fetched"
      ? "Not fetched"
      : currentStatus === "fetching"
        ? "Fetching..."
        : currentStatus === "completed"
          ? "Completed"
          : "Failed";

  return (
    <tr className="border-b border-border/40 hover:bg-muted/10">
      <td className="p-3">
        <p className="font-medium">{acc.account_name}</p>
        <p className="text-xs font-mono text-muted-foreground">{acc.account_id}</p>
      </td>
      <td className="p-3 font-mono text-xs">{acc.account_id}</td>
      <td className="p-3 text-xs">{acc.email || "—"}</td>
      {tab === "inspector" ? (
        <>
          <td className="p-3 font-semibold">{currentCount ?? "—"}</td>
          <td className={cn("p-3 text-xs font-medium", statusColor)}>
            <div className="flex items-center gap-2">
              {isLoading && <Loader2 className="h-3 w-3 animate-spin" />}
              {statusLabel}
              {currentError && (
                <div className="group relative">
                  <AlertCircle className="h-3 w-3 text-red-400 cursor-help" />
                  <div className="absolute bottom-full right-0 mb-2 bg-red-900 text-red-100 text-xs px-2 py-1 rounded hidden group-hover:block whitespace-nowrap z-10">
                    {currentError}
                  </div>
                </div>
              )}
            </div>
          </td>
        </>
      ) : (
        <>
          <td className="p-3">
            {accountCspmScores ? (
              <div className="flex flex-col">
                <span className="font-semibold text-blue-400">{accountCspmScores.cis_score !== undefined && accountCspmScores.cis_score !== null ? accountCspmScores.cis_score.toFixed(1) : "—"}%</span>
                <span className="text-xs text-muted-foreground">({accountCspmScores.cis_pass} pass, {accountCspmScores.cis_fail} fail)</span>
              </div>
            ) : (
              <div className="text-muted-foreground">—</div>
            )}
          </td>

          <td className="p-3">
            {accountCspmScores ? (
              <div className="flex flex-col">
                <span className="font-semibold text-green-400">{accountCspmScores.nist_score !== undefined && accountCspmScores.nist_score !== null ? accountCspmScores.nist_score.toFixed(1) : "—"}%</span>
                <span className="text-xs text-muted-foreground">({accountCspmScores.nist_pass} pass, {accountCspmScores.nist_fail} fail)</span>
              </div>
            ) : (
              <div className="text-muted-foreground">—</div>
            )}
          </td>

          <td className={cn("p-3 text-xs font-medium", statusColor)}>
            <div className="flex items-center gap-2">
              {isLoading && <Loader2 className="h-3 w-3 animate-spin" />}
              {statusLabel}
              {currentError && (
                <div className="group relative">
                  <AlertCircle className="h-3 w-3 text-red-400 cursor-help" />
                  <div className="absolute bottom-full right-0 mb-2 bg-red-900 text-red-100 text-xs px-2 py-1 rounded hidden group-hover:block whitespace-nowrap z-10">
                    {currentError}
                  </div>
                </div>
              )}
            </div>
          </td>
        </>
      )}
      <td className="p-3 flex gap-2">
        {currentStatus === "not_fetched" && (
          <button
            onClick={onFetch}
            disabled={isLoading}
            className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/20 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                Fetching…
              </>
            ) : (
              `Fetch ${tab === "inspector" ? "Inspector" : "CSPM"}`
            )}
          </button>
        )}
        {currentStatus === "fetching" && (
          <button disabled className="inline-flex items-center gap-1 rounded-md bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-400 disabled:opacity-50">
            <Loader2 className="h-3 w-3 animate-spin" />
            Fetching…
          </button>
        )}
        {currentStatus === "completed" && (
          <>
            <button
              onClick={onEmail}
              className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/20"
            >
              <Mail className="h-3 w-3" />
              Email
            </button>
            <button
              onClick={onFetch}
              className="inline-flex items-center gap-1 rounded-md bg-muted/20 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted/40"
            >
              <RefreshCw className="h-3 w-3" />
              Refetch
            </button>
          </>
        )}
        {currentStatus === "failed" && (
          <button
            onClick={onFetch}
            className="inline-flex items-center gap-1 rounded-md bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/20"
          >
            <RefreshCw className="h-3 w-3" />
            Retry
          </button>
        )}
      </td>
    </tr>
  );
}
