"use client";

import { Activity, Bell, CandlestickChart, Menu, RefreshCw, ShieldCheck, Sparkles, WalletCards } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { MarketChart } from "@/components/dashboard/market-chart";
import { MarketHeatmap } from "@/components/dashboard/heatmap";
import { MetricCard } from "@/components/dashboard/metric-card";
import { RankingTable } from "@/components/dashboard/ranking-table";
import { Sidebar, type DashboardSection } from "@/components/dashboard/sidebar";

export function DashboardShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<DashboardSection>("overview");

  const navigate = (section: DashboardSection) => {
    setActiveSection(section);
    document.getElementById(`hawk-${section}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return <div className="min-h-screen bg-[#070b13]">
    <div className="flex min-h-screen">
      <Sidebar open={sidebarOpen} activeSection={activeSection} onClose={() => setSidebarOpen(false)} onNavigate={navigate} />
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
          <section id="hawk-overview" tabIndex={-1} className="mb-6 scroll-mt-20 flex flex-col justify-between gap-4 outline-none md:flex-row md:items-end">
            <div><div className="mb-2 flex items-center gap-2 text-primary"><Sparkles className="h-4 w-4" /><span className="text-xs font-semibold uppercase tracking-[.16em]">Inteligência quantitativa</span></div><h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Visão do mercado</h1><p className="mt-1 text-sm text-muted-foreground">Ranking dinâmico, calculado exclusivamente a partir da evidência coletada.</p></div>
            <div className="flex items-center gap-2 rounded-lg border border-white/[.07] bg-card/70 px-3 py-2 text-xs"><ShieldCheck className="h-4 w-4 text-primary" /><span className="text-muted-foreground">Modelo</span><span className="font-semibold">calibração dinâmica</span><span className="ml-1 text-emerald-400">●</span></div>
          </section>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Coleta pública" value="Ativa" detail="CoinGecko e Binance a cada ciclo" icon={Activity} />
            <MetricCard title="Ranking" value="Em calibração" detail="Aparece após a janela de evidência" icon={Sparkles} />
            <MetricCard title="Dados derivados" value="Opcional" detail="Adicione chaves dos provedores quando quiser" icon={WalletCards} />
            <MetricCard title="Acesso" value="Pessoal" detail="Sem login ou assinatura" icon={CandlestickChart} />
          </section>
          <section id="hawk-analytics" tabIndex={-1} className="mt-4 scroll-mt-20 grid gap-4 outline-none xl:grid-cols-3"><MarketChart /><MarketHeatmap /></section>
          <section id="hawk-scanner" tabIndex={-1} className="mt-4 scroll-mt-20 outline-none"><RankingTable /></section>
          <section className="mt-4 grid gap-4 lg:grid-cols-2">
            <article id="hawk-watchlists" tabIndex={-1} className="panel scroll-mt-20 p-5 outline-none"><p className="text-xs font-semibold uppercase tracking-[.14em] text-primary">Watchlists</p><h2 className="mt-2 text-base font-semibold">Lista pessoal de monitoramento</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">Marque ativos no ranking para acompanhá-los neste espaço assim que a primeira janela calibrada estiver disponível.</p></article>
            <article id="hawk-alerts" tabIndex={-1} className="panel scroll-mt-20 p-5 outline-none"><p className="text-xs font-semibold uppercase tracking-[.14em] text-primary">Alerts</p><h2 className="mt-2 text-base font-semibold">Sinais acima do limiar</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">Os alertas são gerados quando o Hawk Score ultrapassa o limiar configurado. As entregas aparecem aqui após a primeira detecção.</p></article>
          </section>
          <section className="mt-4 grid gap-4 lg:grid-cols-2">
            <article id="hawk-integrity" tabIndex={-1} className="panel scroll-mt-20 p-5 outline-none"><p className="text-xs font-semibold uppercase tracking-[.14em] text-primary">Data integrity</p><h2 className="mt-2 text-base font-semibold">Proveniência da evidência</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">Cada ciclo registra as fontes consultadas, os dados persistidos e a versão usada no cálculo do score.</p></article>
            <article id="hawk-settings" tabIndex={-1} className="panel scroll-mt-20 p-5 outline-none"><p className="text-xs font-semibold uppercase tracking-[.14em] text-primary">Settings</p><h2 className="mt-2 text-base font-semibold">Configuração operacional</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">O ciclo público é executado a cada 10 minutos. Provedores adicionais e canais de alerta podem ser conectados sem alterar o modelo do score.</p></article>
          </section>
        </div>
      </main>
    </div>
  </div>;
}
