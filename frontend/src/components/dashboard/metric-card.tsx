"use client";

import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn, formatNumber } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: LucideIcon;
  trend?: number;
  variant?: "default" | "critical" | "high" | "success" | "info";
  suffix?: string;
}

const variants = {
  default: "text-primary",
  critical: "text-red-500",
  high: "text-orange-500",
  success: "text-emerald-500",
  info: "text-sky-500",
};

export function MetricCard({ title, value, subtitle, icon: Icon, trend, variant = "default", suffix }: MetricCardProps) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <Card className="group hover:shadow-glow transition-shadow duration-300 overflow-hidden">
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{title}</p>
              <p className={cn("mt-2 text-3xl font-bold tabular-nums", variants[variant])}>
                {typeof value === "number" ? formatNumber(value) : value}
                {suffix}
              </p>
              {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
              {trend !== undefined && (
                <p className={cn("mt-2 text-xs font-medium", trend >= 0 ? "text-red-400" : "text-emerald-400")}>
                  {trend >= 0 ? "↑" : "↓"} {Math.abs(trend)}% vs prior period
                </p>
              )}
            </div>
            <div className="rounded-xl bg-primary/10 p-3 ring-1 ring-primary/20 group-hover:bg-primary/15 transition-colors">
              <Icon className={cn("h-5 w-5", variants[variant])} />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
