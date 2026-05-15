"use client";

import { useEffect, useState } from "react";
import { Loader2, Send, X } from "lucide-react";
import { api, AccountRow } from "@/lib/api";

interface Props {
  accountIds: string[];
  accounts: AccountRow[];
  onClose: () => void;
  onSent: () => void;
}

export function EmailComposeDialog({ accountIds, accounts, onClose, onSent }: Props) {
  const [to, setTo] = useState("");
  const [cc, setCc] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .composeEmailPreview(accountIds)
      .then((preview) => {
        setSubject(preview.subject);
        setBody(preview.body_html);
        setTo(preview.suggested_to.join(", "));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [accountIds]);

  const handleSend = async () => {
    setSending(true);
    setError(null);
    try {
      await api.sendEmail({
        account_ids: accountIds,
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

  const selectedNames = accounts
    .filter((a) => accountIds.includes(a.account_id))
    .map((a) => a.account_name)
    .join(", ");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-border bg-card shadow-2xl animate-slide-up max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold">Send Security Report</h2>
            <p className="text-sm text-muted-foreground truncate max-w-md">{selectedNames}</p>
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
            <p className="mt-2 text-muted-foreground">Report and chart attached. Logged for future reference.</p>
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
                Attachments: combined XLSX (Inspector + CSPM for {accountIds.length} account(s)) and findings chart PNG.
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
                Send report for <strong>{accountIds.length}</strong> account(s) to{" "}
                <strong>{to.split(",")[0]}</strong>
                {accountIds.length > 1 ? " (single email with combined attachments)" : ""}?
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
