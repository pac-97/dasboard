"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AgGridReact } from "ag-grid-react";
import { AllCommunityModule, ColDef, ModuleRegistry, ValueFormatterParams } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import { Loader2 } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SeverityChart } from "@/components/charts/severity-chart";
import { api, InspectorFinding } from "@/lib/api";

ModuleRegistry.registerModules([AllCommunityModule]);

export default function InspectorPage() {
  const [accountId, setAccountId] = useState("");
  const [severity, setSeverity] = useState("");

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["inspector-summary"],
    queryFn: () => api.inspectorSummary(false),
  });

  const { data: findings = [], isLoading } = useQuery({
    queryKey: ["inspector-findings", accountId, severity],
    queryFn: () =>
      api.inspectorFindings({
        ...(accountId && { account_id: accountId }),
        ...(severity && { severity }),
        page_size: "200",
      }),
  });

  const columns: ColDef<InspectorFinding>[] = [
    { field: "account_id", headerName: "Account", filter: true, width: 140 },
    { field: "severity", headerName: "Severity", filter: true, width: 110 },
    { field: "title", headerName: "Title", flex: 2, filter: true },
    { field: "region", headerName: "Region", filter: true, width: 120 },
    { field: "cve_ids", headerName: "CVE", filter: true, width: 140 },
    {
      field: "fix_available",
      headerName: "Fix Available",
      width: 120,
      valueFormatter: (p: ValueFormatterParams<InspectorFinding, boolean | null>) => (p.value ? "Yes" : "No"),
    },
    { field: "status", headerName: "Status", width: 100 },
  ];

  return (
    <div>
      <Topbar title="Inspector Findings" subtitle="Live organization-wide vulnerability data" />
      <div className="space-y-6 p-8">
        <div className="flex flex-wrap gap-3">
          <input
            placeholder="Filter by account ID"
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            className="rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm"
          >
            <option value="">All severities</option>
            {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Findings Grid</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex justify-center py-20">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <div className="ag-theme-quartz-dark h-[480px] w-full rounded-lg overflow-hidden">
                  <AgGridReact
                    rowData={findings}
                    columnDefs={columns}
                    pagination
                    paginationPageSize={25}
                    defaultColDef={{ sortable: true, resizable: true }}
                  />
                </div>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Severity Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              {summaryLoading ? (
                <Loader2 className="h-6 w-6 animate-spin mx-auto" />
              ) : summary ? (
                <SeverityChart data={summary.severity_distribution} />
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
