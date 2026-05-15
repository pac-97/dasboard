"use client";

import { useQuery } from "@tanstack/react-query";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Cog, Mail, AlertCircle, Calendar } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const demoOps = {
  stats: { total_jobs: 156, failed_jobs: 3, emails_sent: 1420, emails_failed: 8, active_schedules: 4 },
  recent_jobs: [
    { id: 156, type: "full_pipeline", status: "completed" },
    { id: 155, type: "full_pipeline", status: "failed" },
    { id: 154, type: "full_pipeline", status: "completed" },
  ],
  email_logs: [
    { recipient: "jane.smith@company.com", status: "sent", subject: "AWS Security Report — Jane Smith" },
    { recipient: "john.doe@company.com", status: "sent", subject: "AWS Security Report — John Doe" },
  ],
  audit_history: [
    { action: "job.trigger", actor: "scheduler", created_at: new Date().toISOString() },
    { action: "owner.import", actor: "admin", created_at: new Date().toISOString() },
  ],
};

export default function OperationsPage() {
  const { data = demoOps } = useQuery({
    queryKey: ["operations"],
    queryFn: api.operations,
    placeholderData: demoOps,
  });

  const statusColor: Record<string, string> = {
    completed: "text-emerald-400 bg-emerald-500/10",
    failed: "text-red-400 bg-red-500/10",
    running: "text-blue-400 bg-blue-500/10",
    pending: "text-yellow-400 bg-yellow-500/10",
  };

  return (
    <div>
      <Topbar title="Operations" subtitle="Jobs, email delivery, scheduling & audit" />
      <div className="space-y-6 p-8">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard title="Total Jobs" value={data.stats.total_jobs} icon={Cog} />
          <MetricCard title="Failed Jobs" value={data.stats.failed_jobs} icon={AlertCircle} variant="critical" />
          <MetricCard title="Emails Sent" value={data.stats.emails_sent} icon={Mail} variant="success" />
          <MetricCard title="Active Schedules" value={data.stats.active_schedules} icon={Calendar} variant="info" />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Job Execution History</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {data.recent_jobs.map((job) => (
                <div key={job.id} className="flex items-center justify-between rounded-lg bg-muted/20 px-4 py-3">
                  <div>
                    <p className="font-medium">Job #{job.id}</p>
                    <p className="text-xs text-muted-foreground">{job.type}</p>
                  </div>
                  <span className={cn("rounded-full px-3 py-1 text-xs font-medium capitalize", statusColor[job.status] || "")}>
                    {job.status}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Email Delivery Logs</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {data.email_logs.map((log, i) => (
                <div key={i} className="rounded-lg bg-muted/20 px-4 py-3">
                  <div className="flex justify-between">
                    <p className="text-sm font-medium truncate">{log.recipient}</p>
                    <span className={cn("text-xs", log.status === "sent" ? "text-emerald-400" : "text-red-400")}>{log.status}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 truncate">{log.subject}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Audit History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {data.audit_history.map((entry, i) => (
                <div key={i} className="flex justify-between rounded-lg border border-border/50 px-4 py-2 text-sm">
                  <span className="font-mono text-primary">{entry.action}</span>
                  <span className="text-muted-foreground">{entry.actor}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
