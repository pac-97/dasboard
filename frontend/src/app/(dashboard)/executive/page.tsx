"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AlertTriangle, Shield, TrendingUp, Activity, Target, BarChart3, Loader2 } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { SeverityChart } from "@/components/charts/severity-chart";
import { RegionHeatmap } from "@/components/charts/heatmap-chart";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ExecutivePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["executive"],
    queryFn: () => api.executive(false),
  });

  if (isLoading) {
    return (
      <div>
        <Topbar title="Executive Overview" subtitle="Loading live AWS data…" showRefresh={false} />
        <div className="flex items-center justify-center py-32 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin mr-3" />
          Fetching organization-wide findings from AWS…
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <Topbar title="Executive Overview" />
        <div className="p-8 text-red-400">{(error as Error)?.message || "Failed to load data"}</div>
      </div>
    );
  }

  return (
    <div>
      <Topbar title="Executive Overview" subtitle={`Live posture · ${data.total_findings.toLocaleString()} findings`} />
      <div className="space-y-6 p-8">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
          <MetricCard title="Total Findings" value={data.total_findings} icon={Activity} />
          <MetricCard title="Critical" value={data.critical_findings} icon={AlertTriangle} variant="critical" />
          <MetricCard title="High" value={data.high_findings} icon={TrendingUp} variant="high" />
          <MetricCard title="Compliance" value={data.compliance_score} suffix="%" icon={Shield} variant="success" />
          <MetricCard title="CIS Score" value={data.cis_score} suffix="%" icon={Target} variant="info" />
          <MetricCard title="NIST Score" value={data.nist_score} suffix="%" icon={BarChart3} variant="info" />
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Top Risky Accounts</CardTitle>
              <CardDescription>From live Inspector data</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.top_risky_accounts.map((acc, i) => (
                <motion.div
                  key={acc.account_id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center justify-between rounded-lg bg-muted/20 px-4 py-3 ring-1 ring-border/50"
                >
                  <div>
                    <p className="font-medium">{acc.account_name}</p>
                    <p className="text-xs text-muted-foreground font-mono">{acc.account_id}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-red-400">{acc.critical} critical</p>
                    <p className="text-xs text-muted-foreground">Score {acc.risk_score}</p>
                  </div>
                </motion.div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Severity Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <SeverityChart data={data.severity_distribution} />
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Resource Exposure by Region</CardTitle>
          </CardHeader>
          <CardContent>
            <RegionHeatmap data={data.resource_exposure} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Most Vulnerable Services</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {data.most_vulnerable_services.map((svc, i) => (
                <div
                  key={svc.service}
                  className={cn(
                    "rounded-xl p-4 ring-1 ring-border/50 bg-gradient-to-br from-muted/20 to-transparent",
                    i === 0 && "ring-primary/30"
                  )}
                >
                  <p className="text-xs text-muted-foreground truncate">{svc.service}</p>
                  <p className="mt-1 text-2xl font-bold">{svc.count.toLocaleString()}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
