"use client";

import { useQuery } from "@tanstack/react-query";
import { Users, Mail, FileText } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

const demoOwners = [
  { id: 1, name: "Jane Smith", email: "jane.smith@company.com", accounts: ["111122223333", "444455556666"] },
  { id: 2, name: "John Doe", email: "john.doe@company.com", accounts: ["777788889999"] },
];

export default function OwnersPage() {
  const { data: owners = demoOwners } = useQuery({
    queryKey: ["owners"],
    queryFn: api.owners,
    placeholderData: demoOwners,
  });

  return (
    <div>
      <Topbar title="Account Owners" subtitle="Owner consolidation · single email per owner" />
      <div className="space-y-6 p-8">
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardContent className="flex items-center gap-4 p-6">
              <Users className="h-8 w-8 text-primary" />
              <div>
                <p className="text-2xl font-bold">{owners.length}</p>
                <p className="text-sm text-muted-foreground">Registered owners</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-4 p-6">
              <Mail className="h-8 w-8 text-emerald-500" />
              <div>
                <p className="text-2xl font-bold">Weekly</p>
                <p className="text-sm text-muted-foreground">Email cadence</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-4 p-6">
              <FileText className="h-8 w-8 text-violet-500" />
              <div>
                <p className="text-2xl font-bold">XLSX</p>
                <p className="text-sm text-muted-foreground">Report attachments</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Owner Directory</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {owners.map((owner) => (
                <div
                  key={owner.id}
                  className="rounded-xl border border-border/50 bg-muted/10 p-5 hover:bg-muted/20 transition-colors"
                >
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="font-semibold text-lg">{owner.name}</p>
                      <p className="text-sm text-muted-foreground">{owner.email}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {owner.accounts.map((acc) => (
                        <span key={acc} className="rounded-md bg-primary/10 px-2 py-1 text-xs font-mono text-primary">
                          {acc}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
