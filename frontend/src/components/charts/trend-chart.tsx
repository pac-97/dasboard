"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

export function TrendChart({
  data,
}: {
  data: { date: string; critical: number; high: number; total: number }[];
}) {
  const formatted = data.map((d) => ({
    ...d,
    label: d.date ? new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "",
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <AreaChart data={formatted}>
        <defs>
          <linearGradient id="criticalGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#EF4444" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 33% 18%)" />
        <XAxis dataKey="label" stroke="#64748B" fontSize={12} />
        <YAxis stroke="#64748B" fontSize={12} />
        <Tooltip
          contentStyle={{ background: "hsl(222 47% 9%)", border: "1px solid hsl(217 33% 18%)", borderRadius: 8 }}
        />
        <Legend />
        <Area type="monotone" dataKey="critical" stroke="#EF4444" fill="url(#criticalGrad)" strokeWidth={2} />
        <Area type="monotone" dataKey="high" stroke="#F97316" fill="transparent" strokeWidth={2} />
        <Area type="monotone" dataKey="total" stroke="#3B82F6" fill="url(#totalGrad)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
