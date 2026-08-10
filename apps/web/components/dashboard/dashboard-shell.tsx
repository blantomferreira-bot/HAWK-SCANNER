"use client";

import { Activity, Bell, CandlestickChart, Menu, RefreshCw, ShieldCheck, Sparkles, WalletCards } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { MarketChart } from "@/components/dashboard/market-chart";
import { MarketHeatmap } from "@/components/dashboard/heatmap";
import { MetricCard } from "@/components/dashboard/metric-card";
import { RankingTable } from "@/components/dashboard/ranking-table";
import { Sidebar } from "@/components/dashboard/sidebar";

export function DashboardShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return <div className="min-h-screen bg-[#070b13]">
    <div className="flex min-h-screen">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/[.07] bg-[#070b13]/90 px-4 backdrop-blur-xl sm:px-6">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(true)} aria-label="Abrir navegação"><Menu className="h-5 w-5" /></Button>
            <div className="hidden items-center gap-2 text-xs text-muted-foreground sm:flex"><span>Terminal pessoal</span><span className="text-slate-600">/</span><span className="font-medium text-foreground">Visão do mercado</span></div>
            <span className="rounded bg-primary/10 px-2 py-1 text-[10px] font-semibold text-primary">AO VIVO</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-2 rounded-lg border border-white/[.07] bg-white/[.025] px-2.5 py-1.5 text-[11px] text-muted-foreground md:flex"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />Ciclo automático ativo</div>
            <Button variant="ghost" size="icon" className="relative" aria-label="Alertas"><Bell className="h-4 w-4" /></Button>
            <Button variant="outline" size="sm" className="hidden sm:flex" onClick={() => window.location.reload()}><RefreshCw className="h-3.5 w-3.5" />Atualizar</Button>
          </div>
        </header>
        <div className="data-grid bg-grid px-4 py-6 sm:px-6 lg:px-8">
          <section className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
            <div><div className="mb-2 flex items-center gap-2 text-primary"><Sparkles className="h-4 w-4" /><span className="text-xs font-semibold uppercase tracking-[.16em]">Inteligência quantitativa</span></div><h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Visão do mercado</h1><p className="mt-1 text-sm text-muted-foreground">Ranking dinâmico, calculado exclusivamente a partir da evidência coletada.</p></div>
            <div className="flex items-center gap-2 rounded-lg border border-white/[.07] bg-card/70 px-3 py-2 text-xs"><ShieldCheck className="h-4 w-4 text-primary" /><span className="text-muted-foreground">Modelo</span><span className="font-semibold">calibração dinâmica</span><span className="ml-1 text-emerald-400">●</span></div>
          </section>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Coleta pública" value="Ativa" detail="CoinGecko e Binance a cada ciclo" icon={Activity} />
            <MetricCard title="Ranking" value="Em calibração" detail="Aparece após a janela de evidência" icon={Sparkles} />
            <MetricCard title="Dados derivados" value="Opcional" detail="Adicione chaves dos provedores quando quiser" icon={WalletCards} />
            <MetricCard title="Acesso" value="Pessoal" detail="Sem login ou assinatura" icon={CandlestickChart} />
          </section>
          <section className="mt-4 grid gap-4 xl:grid-cols-3"><MarketChart /><MarketHeatmap /></section>
          <section className="mt-4"><RankingTable /></section>
        </div>
      </main>
    </div>
  </div>;
}
