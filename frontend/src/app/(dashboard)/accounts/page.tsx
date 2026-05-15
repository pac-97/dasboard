"use client";

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Mail, RefreshCw, Search, CheckSquare, Square } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmailComposeDialog } from "@/components/email/email-compose-dialog";
import { api, AccountRow } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function AccountsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [emailOpen, setEmailOpen] = useState(false);
  const [emailAccounts, setEmailAccounts] = useState<string[]>([]);
  const [tab, setTab] = useState<"accounts" | "logs">("accounts");
  const [logMonth, setLogMonth] = useState("");

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ["accounts-live"],
    queryFn: () => api.accountsLive(false),
    refetchOnWindowFocus: false,
  });

  const { data: emailLogs } = useQuery({
    queryKey: ["email-logs", logMonth],
    queryFn: () => api.emailLogs(logMonth || undefined),
    enabled: tab === "logs",
  });

  const accounts = data?.accounts ?? [];
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return accounts;
    return accounts.filter(
      (a) =>
        a.account_name.toLowerCase().includes(q) ||
        a.account_id.includes(q) ||
        (a.owner_email || "").toLowerCase().includes(q)
    );
  }, [accounts, search]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === filtered.length) setSelected(new Set());
    else setSelected(new Set(filtered.map((a) => a.account_id)));
  };

  const openEmail = (ids: string[]) => {
    setEmailAccounts(ids);
    setEmailOpen(true);
  };

  const fetchedLabel = data?.fetched_at
    ? new Date(data.fetched_at * 1000).toLocaleString()
    : "—";

  return (
    <div>
      <Topbar
        title="Accounts & Email"
        subtitle={`Live AWS data · ${data?.account_count ?? "—"} accounts · Last fetch: ${fetchedLabel}`}
      />

      <div className="px-8 pt-4 flex gap-2 border-b border-border/50">
        <button
          onClick={() => setTab("accounts")}
          className={cn("px-4 py-2 text-sm font-medium rounded-t-lg", tab === "accounts" ? "bg-card text-primary" : "text-muted-foreground")}
        >
          All Accounts
        </button>
        <button
          onClick={() => setTab("logs")}
          className={cn("px-4 py-2 text-sm font-medium rounded-t-lg", tab === "logs" ? "bg-card text-primary" : "text-muted-foreground")}
        >
          Email Logs
        </button>
      </div>

      <div className="p-8 space-y-4">
        {tab === "accounts" && (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[200px] max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search account, ID, owner…"
                  className="w-full rounded-lg border border-border bg-muted/30 py-2 pl-10 pr-4 text-sm"
                />
              </div>
              <button
                onClick={() => refetch()}
                disabled={isFetching}
                className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm hover:bg-muted"
              >
                <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
                Refresh from AWS
              </button>
              {selected.size > 0 && (
                <button
                  onClick={() => openEmail(Array.from(selected))}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground"
                >
                  <Mail className="h-4 w-4" />
                  Email {selected.size} Selected
                </button>
              )}
            </div>

            {error && (
              <Card className="border-red-500/30 bg-red-500/5">
                <CardContent className="p-4 text-sm text-red-400">
                  Failed to load AWS data: {(error as Error).message}. Ensure EC2 has delegated-account AWS CLI credentials.
                </CardContent>
              </Card>
            )}

            {isLoading ? (
              <div className="text-center py-20 text-muted-foreground">Fetching live findings from AWS…</div>
            ) : (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Organization Accounts</CardTitle>
                  <button onClick={toggleAll} className="text-xs text-primary hover:underline">
                    {selected.size === filtered.length ? "Deselect all" : "Select all visible"}
                  </button>
                </CardHeader>
                <CardContent className="overflow-x-auto p-0">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-muted/20 text-left text-muted-foreground">
                        <th className="p-3 w-10" />
                        <th className="p-3">Account</th>
                        <th className="p-3">Inspector</th>
                        <th className="p-3">Critical</th>
                        <th className="p-3">High</th>
                        <th className="p-3">CSPM Score</th>
                        <th className="p-3">CIS</th>
                        <th className="p-3">NIST</th>
                        <th className="p-3">Owner</th>
                        <th className="p-3">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((acc) => (
                        <AccountTableRow
                          key={acc.account_id}
                          acc={acc}
                          selected={selected.has(acc.account_id)}
                          onToggle={() => toggle(acc.account_id)}
                          onEmail={() => openEmail([acc.account_id])}
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
  selected,
  onToggle,
  onEmail,
}: {
  acc: AccountRow;
  selected: boolean;
  onToggle: () => void;
  onEmail: () => void;
}) {
  const scoreColor =
    acc.cspm_score >= 80 ? "text-emerald-400" : acc.cspm_score >= 60 ? "text-yellow-400" : "text-red-400";

  return (
    <tr className="border-b border-border/40 hover:bg-muted/10">
      <td className="p-3">
        <button onClick={onToggle} className="text-muted-foreground hover:text-primary">
          {selected ? <CheckSquare className="h-4 w-4 text-primary" /> : <Square className="h-4 w-4" />}
        </button>
      </td>
      <td className="p-3">
        <p className="font-medium">{acc.account_name}</p>
        <p className="text-xs font-mono text-muted-foreground">{acc.account_id}</p>
      </td>
      <td className="p-3 font-semibold">{acc.inspector_total}</td>
      <td className="p-3 text-red-400 font-medium">{acc.inspector_critical}</td>
      <td className="p-3 text-orange-400 font-medium">{acc.inspector_high}</td>
      <td className={cn("p-3 font-bold", scoreColor)}>{acc.cspm_score}%</td>
      <td className="p-3">{acc.cis_score}%</td>
      <td className="p-3">{acc.nist_score}%</td>
      <td className="p-3 text-xs">{acc.owner_email || acc.owner_name || "—"}</td>
      <td className="p-3">
        <button
          onClick={onEmail}
          className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/20"
        >
          <Mail className="h-3 w-3" />
          Send Email
        </button>
      </td>
    </tr>
  );
}
