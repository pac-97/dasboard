"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Shield,
  ScanSearch,
  Users,
  Settings2,
  ShieldAlert,
} from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/executive", label: "Executive", icon: LayoutDashboard },
  { href: "/inspector", label: "Inspector", icon: ScanSearch },
  { href: "/cspm", label: "CSPM", icon: Shield },
  { href: "/accounts", label: "Accounts & Email", icon: Users },
  { href: "/operations", label: "Operations", icon: Settings2 },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col border-r border-border/50 bg-card/40 backdrop-blur-2xl">
      <div className="flex h-16 items-center gap-3 border-b border-border/50 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 shadow-lg shadow-blue-500/25">
          <ShieldAlert className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight">AWS Security</p>
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Command Center</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {nav.map((item) => {
          const active = pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href}>
              <motion.div
                className={cn(
                  "relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  active ? "text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                )}
                whileHover={{ x: 2 }}
              >
                {active && (
                  <motion.div
                    layoutId="sidebar-active"
                    className="absolute inset-0 rounded-lg bg-primary/10 ring-1 ring-primary/30"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.5 }}
                  />
                )}
                <Icon className={cn("relative h-4 w-4", active && "text-primary")} />
                <span className="relative">{item.label}</span>
              </motion.div>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border/50 p-4">
        <div className="rounded-lg bg-muted/30 p-3 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">82 Accounts</p>
          <p className="mt-1">Organization-wide posture</p>
        </div>
      </div>
    </aside>
  );
}
