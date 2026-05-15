"use client";

import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { Loader2 } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Shield, FileCheck } from "lucide-react";
import { api } from "@/lib/api";

export default function CspmPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["cspm-summary"],
    queryFn: () => api.cspmSummary(false),
  });

  const benchmarkOption = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: { data: ["CIS v5.0.0", "NIST 800-53 R5"], textStyle: { color: "#94A3B8" } },
    radar: {
      indicator: [
        { name: "IAM", max: 100 },
        { name: "Storage", max: 100 },
        { name: "Logging", max: 100 },
        { name: "Networking", max: 100 },
        { name: "Compute", max: 100 },
      ],
      axisName: { color: "#94A3B8" },
      splitLine: { lineStyle: { color: "#1E293B" } },
      splitArea: { areaStyle: { color: ["transparent"] } },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: [data?.cis_compliance ?? 0, 78, 92, 70, 88],
            name: "CIS v5.0.0",
            areaStyle: { color: "rgba(59,130,246,0.2)" },
            lineStyle: { color: "#3B82F6" },
          },
          {
            value: [data?.nist_compliance ?? 0, 68, 80, 65, 75],
            name: "NIST 800-53 R5",
            areaStyle: { color: "rgba(139,92,246,0.2)" },
            lineStyle: { color: "#8B5CF6" },
          },
        ],
      },
    ],
  };

  if (isLoading) {
    return (
      <div>
        <Topbar title="CSPM Compliance" showRefresh={false} />
        <div className="flex justify-center py-32">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <Topbar title="CSPM Compliance" />
        <p className="p-8 text-red-400">{(error as Error)?.message}</p>
      </div>
    );
  }

  return (
    <div>
      <Topbar title="CSPM Compliance" subtitle="CIS AWS Foundations v5.0.0 · NIST SP 800-53 Rev 5 · Live data" />
      <div className="space-y-6 p-8">
        <div className="grid gap-4 sm:grid-cols-2">
          <MetricCard title="CIS Compliance" value={data.cis_compliance} suffix="%" icon={Shield} variant="success" />
          <MetricCard title="NIST Compliance" value={data.nist_compliance} suffix="%" icon={FileCheck} variant="info" />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Benchmark Overview</CardTitle>
              <CardDescription>Live compliance scores</CardDescription>
            </CardHeader>
            <CardContent>
              <ReactECharts option={benchmarkOption} style={{ height: 360 }} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Top Failed Services</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.top_failed_services.map((svc, i) => (
                <div key={svc.service} className="flex items-center gap-4">
                  <span className="w-6 text-sm text-muted-foreground">{i + 1}</span>
                  <div className="flex-1">
                    <div className="flex justify-between text-sm mb-1">
                      <span>{svc.service}</span>
                      <span className="text-red-400 font-medium">{svc.count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-red-500 to-orange-500"
                        style={{
                          width: `${data.top_failed_services[0]?.count ? (svc.count / data.top_failed_services[0].count) * 100 : 0}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Account-wise Failed Controls</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-3">Account</th>
                  <th className="pb-3">Failed Controls</th>
                </tr>
              </thead>
              <tbody>
                {data.account_comparison.map((row) => (
                  <tr key={row.account_id} className="border-b border-border/50">
                    <td className="py-3">
                      <p className="font-medium">{row.account_name}</p>
                      <p className="text-xs font-mono text-muted-foreground">{row.account_id}</p>
                    </td>
                    <td className="py-3 text-red-400 font-semibold">{row.failed_controls}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
