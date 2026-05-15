"use client";

import { useTheme } from "next-themes";
import { Moon, Sun, RefreshCw } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export function Topbar({ title, subtitle, showRefresh = true }: { title: string; subtitle?: string; showRefresh?: boolean }) {
  const { theme, setTheme } = useTheme();
  const qc = useQueryClient();
  const refresh = useMutation({
    mutationFn: () => api.refreshAccounts(),
    onSuccess: () => qc.invalidateQueries(),
  });

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border/50 bg-background/60 px-8 backdrop-blur-xl">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">
        {showRefresh && (
          <button
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("h-4 w-4", refresh.isPending && "animate-spin")} />
            Refresh AWS Data
          </button>
        )}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="rounded-lg p-2 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>
      </div>
    </header>
  );
}
