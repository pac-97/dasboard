"use client";

import { useEffect, useState } from "react";
import { Loader2, Send, X, Check } from "lucide-react";
import { api, AccountRow } from "@/lib/api";

interface Props {
  accountIds: string[];
  findingType: "inspector" | "cspm";
  accounts: AccountRow[];
  onClose: () => void;
  onSent: () => void;
}

export function EmailComposeDialog({ accountIds, findingType, accounts, onClose, onSent }: Props) {
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>(accountIds);
  const [to, setTo] = useState("");
  const [cc, setCc] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAccountSelector, setShowAccountSelector] = useState(false);

  // Update preview when selected accounts change
  useEffect(() => {
    setLoading(true);
    api
      .composeEmailPreview(selectedAccountIds, findingType)
      .then((preview) => {
        setSubject(preview.subject);
        setBody(preview.body_html);
        setTo(preview.suggested_to.join(", "));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedAccountIds, findingType]);

  const handleSend = async () => {
    setSending(true);
    setError(null);
    try {
      await api.sendEmail({
        account_ids: selectedAccountIds,
        finding_type: findingType,
        to_emails: to.split(",").map((e) => e.trim()).filter(Boolean),
        cc_emails: cc.split(",").map((e) => e.trim()).filter(Boolean),
        subject,
        body_html: body,
      });
      setSuccess(true);
      setConfirmOpen(false);
      onSent();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Send failed");
      setConfirmOpen(false);
    } finally {
      setSending(false);
    }
  };

  const toggleAccount = (accountId: string) => {
    setSelectedAccountIds((prev) =>
      prev.includes(accountId) ? prev.filter((id) => id !== accountId) : [...prev, accountId]
    );
  };

  const selectAllAccounts = () => {
    setSelectedAccountIds(accounts.map((a) => a.account_id));
  };

  const deselectAllAccounts = () => {
    setSelectedAccountIds([]);
  };

  const selectedNames = accounts
    .filter((a) => selectedAccountIds.includes(a.account_id))
    .map((a) => a.account_name)
    .join(", ");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-border bg-card shadow-2xl animate-slide-up max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold">Send Security Report</h2>
            <p className="text-sm text-muted-foreground truncate max-w-md">{selectedNames || "No accounts selected"}</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 hover:bg-muted">
            <X className="h-5 w-5" />
          </button>
        </div>

        {success ? (
          <div className="p-10 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/20">
              <Send className="h-8 w-8 text-emerald-500" />
            </div>
            <h3 className="text-xl font-semibold text-emerald-400">Email Sent</h3>
            <p className="mt-2 text-muted-foreground">Consolidated report attached. Logged for future reference.</p>
            <button onClick={onClose} className="mt-6 rounded-lg bg-primary px-6 py-2 text-primary-foreground">
              Close
            </button>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center p-16">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-3 text-muted-foreground">Loading live findings & preparing attachments…</span>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {error && (
                <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">{error}</div>
              )}
              
              {/* Account Selection Section */}
              <div className="border border-border rounded-lg p-4 bg-muted/20">
                <div className="flex items-center justify-between mb-3">
                  <label className="text-xs font-medium uppercase text-muted-foreground">Select Accounts ({selectedAccountIds.length}/{accounts.length})</label>
                  <button
                    onClick={() => setShowAccountSelector(!showAccountSelector)}
                    className="text-xs text-primary hover:underline"
                  >
                    {showAccountSelector ? "Hide" : "Show"}
                  </button>
                </div>
                
                {showAccountSelector && (
                  <>
                    <div className="flex gap-2 mb-3">
                      <button
                        onClick={selectAllAccounts}
                        className="px-3 py-1 text-xs bg-primary/20 text-primary rounded hover:bg-primary/30"
                      >
                        Select All
                      </button>
                      <button
                        onClick={deselectAllAccounts}
                        className="px-3 py-1 text-xs bg-muted text-muted-foreground rounded hover:bg-muted/80"
                      >
                        Deselect All
                      </button>
                    </div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {accounts.map((account) => (
                        <label
                          key={account.account_id}
                          className="flex items-center gap-2 p-2 rounded hover:bg-muted/30 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedAccountIds.includes(account.account_id)}
                            onChange={() => toggleAccount(account.account_id)}
                            className="w-4 h-4 rounded"
                          />
                          <span className="flex-1">
                            {account.account_name} <span className="text-xs text-muted-foreground">({account.account_id})</span>
                          </span>
                          {selectedAccountIds.includes(account.account_id) && (
                            <Check className="h-4 w-4 text-primary" />
                          )}
                        </label>
                      ))}
                    </div>
                  </>
                )}
              </div>

              <div>
                <label className="text-xs font-medium uppercase text-muted-foreground">To</label>
                <input
                  value={to}
                  onChange={(e) => setTo(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm"
                  placeholder="owner@company.com"
                />
              </div>
              <div>
                <label className="text-xs font-medium uppercase text-muted-foreground">CC</label>
                <input
                  value={cc}
                  onChange={(e) => setCc(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm"
                  placeholder="optional@company.com"
                />
              </div>
              <div>
                <label className="text-xs font-medium uppercase text-muted-foreground">Subject</label>
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-medium uppercase text-muted-foreground">Email Body (HTML)</label>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  rows={10}
                  className="mt-1 w-full rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm font-mono"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Attachments: consolidated XLSX report ({selectedAccountIds.length} account{selectedAccountIds.length !== 1 ? 's' : ''}) with Executive Summary, All Failed, Critical, High, and Medium findings sheets.
              </p>
            </div>

            <div className="flex justify-end gap-3 border-t border-border px-6 py-4">
              <button onClick={onClose} className="rounded-lg px-4 py-2 text-sm hover:bg-muted">
                Cancel
              </button>
              <button
                onClick={() => setConfirmOpen(true)}
                disabled={!to.trim() || sending}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                Send Email
              </button>
            </div>
          </>
        )}

        {confirmOpen && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <div className="mx-4 w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
                <h3 className="text-lg font-semibold">Confirm send?</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Send consolidated report for <strong>{selectedAccountIds.length}</strong> account{selectedAccountIds.length !== 1 ? 's' : ''} to{" "}
                  <strong>{to.split(",")[0]}</strong>
                  {selectedAccountIds.length > 1 ? " (single email with combined XLSX attachment)" : ""}?
                </p>
                <div className="mt-6 flex justify-end gap-3">
                  <button onClick={() => setConfirmOpen(false)} className="rounded-lg px-4 py-2 text-sm hover:bg-muted">
                    Cancel
                  </button>
                  <button
                    onClick={handleSend}
                    disabled={sending}
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground"
                  >
                    {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    Confirm & Send
                  </button>
                </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
