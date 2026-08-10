"use client";

import { BarChart3, BellRing, ChevronLeft, Gauge, LayoutDashboard, Settings, ShieldCheck, Star, X, type LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type DashboardSection = "overview" | "scanner" | "analytics" | "watchlists" | "alerts" | "integrity" | "settings";

const navigation: Array<{ icon: LucideIcon; label: string; target: DashboardSection; badge?: string }> = [
  { icon: LayoutDashboard, label: "Overview", target: "overview" },
  { icon: Gauge, label: "Scanner", target: "scanner" },
  { icon: BarChart3, label: "Analytics", target: "analytics" },
  { icon: Star, label: "Watchlists", target: "watchlists" },
  { icon: BellRing, label: "Alerts", target: "alerts" },
];

type SidebarProps = {
  open: boolean;
  activeSection: DashboardSection;
  onClose: () => void;
  onNavigate: (section: DashboardSection) => void;
};

export function Sidebar({ open, activeSection, onClose, onNavigate }: SidebarProps) {
  const [selectedSection, setSelectedSection] = useState(activeSection);

  useEffect(() => setSelectedSection(activeSection), [activeSection]);

  const navigate = (section: DashboardSection) => {
    setSelectedSection(section);
    onNavigate(section);
    onClose();
  };

  const navClassName = (section: DashboardSection) => cn(
    "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
    selectedSection === section ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-white/[.045] hover:text-foreground",
  );

  return <>
    {open && <button aria-label="Fechar navegação" onClick={onClose} className="fixed inset-0 z-30 bg-black/60 lg:hidden" />}
    <aside className={cn("fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-white/[0.07] bg-[#090e19] transition-transform lg:static lg:translate-x-0", open ? "translate-x-0" : "-translate-x-full")}>
      <div className="flex h-16 items-center justify-between border-b border-white/[0.07] px-5">
        <div className="flex items-center gap-3"><div className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-[11px] font-black tracking-tighter text-primary-foreground">H</div><div><p className="text-sm font-bold tracking-[.16em]">HAWK</p><p className="text-[10px] tracking-[.22em] text-primary">SCANNER</p></div></div>
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onClose}><X className="h-4 w-4" /></Button>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        <p className="px-3 pb-2 pt-3 text-[10px] font-semibold uppercase tracking-[.16em] text-muted-foreground">Workspace</p>
        {navigation.map(({ icon: Icon, label, target, badge }) => <button key={label} type="button" onClick={() => navigate(target)} aria-current={selectedSection === target ? "page" : undefined} className={navClassName(target)}><Icon className="h-4 w-4" />{label}{badge && <span className="ml-auto rounded-full bg-rose-500 px-1.5 text-[10px] font-bold text-white">{badge}</span>}</button>)}
        <p className="px-3 pb-2 pt-7 text-[10px] font-semibold uppercase tracking-[.16em] text-muted-foreground">Control</p>
        <button type="button" onClick={() => navigate("integrity")} aria-current={selectedSection === "integrity" ? "page" : undefined} className={navClassName("integrity")}><ShieldCheck className="h-4 w-4" />Data integrity</button>
        <button type="button" onClick={() => navigate("settings")} aria-current={selectedSection === "settings" ? "page" : undefined} className={navClassName("settings")}><Settings className="h-4 w-4" />Settings</button>
      </nav>
      <div className="m-3 rounded-xl border border-primary/20 bg-primary/[.06] p-3"><p className="text-xs font-semibold">HAWK Pro</p><p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">Realtime signal intelligence enabled.</p><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full w-[72%] rounded-full bg-primary" /></div></div>
      <div className="flex items-center gap-3 border-t border-white/[0.07] p-4"><div className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 text-xs font-bold">RS</div><div className="min-w-0"><p className="truncate text-xs font-medium">Research Station</p><p className="text-[10px] text-muted-foreground">Professional</p></div><ChevronLeft className="ml-auto h-4 w-4 text-muted-foreground" /></div>
    </aside>
  </>;
}
