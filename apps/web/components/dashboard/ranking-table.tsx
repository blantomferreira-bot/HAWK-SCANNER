"use client";

import { ArrowDownUp, ChevronDown, Filter, Search, Star } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn, compactCurrency } from "@/lib/utils";

const tabs = ["All signals", "Bullish", "Bearish", "High conviction"] as const;
type Tab = (typeof tabs)[number];

type RankedAsset = {
  rank: number;
  coinId: string;
  symbol: string;
  name: string;
  price: number | null;
  volume: number | null;
  score: number;
  confidence: number;
  signal: "BULLISH" | "BEARISH" | "NEUTRAL";
};

const productionApiBaseUrl = "https://splendid-wholeness-production-f000.up.railway.app/api/v1";

function asNumber(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function SignalBadge({ signal }: { signal: RankedAsset["signal"] }) {
  const variant = signal === "BULLISH" ? "bullish" : signal === "BEARISH" ? "bearish" : "neutral";
  const label = signal === "BULLISH" ? "Long bias" : signal === "BEARISH" ? "Short bias" : "Neutral";
  return <Badge variant={variant}>{label}</Badge>;
}

export function RankingTable() {
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<Tab>("All signals");
  const [ascending, setAscending] = useState(false);
  const [assets, setAssets] = useState<RankedAsset[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const controller = new AbortController();
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? productionApiBaseUrl;

    async function loadRanking() {
      try {
        const response = await fetch(`${baseUrl.replace(/\/$/, "")}/ranking?limit=100`, {
          signal: controller.signal,
          cache: "no-store",
        });
        if (!response.ok) throw new Error(`Ranking request failed: ${response.status}`);
        const payload: { data?: Array<Record<string, unknown>> } = await response.json();
        setAssets((payload.data ?? []).map((item, index) => ({
          rank: index + 1,
          coinId: String(item.coin_id ?? ""),
          symbol: String(item.symbol ?? "—").toUpperCase(),
          name: String(item.name ?? "Unknown asset"),
          price: asNumber(item.price),
          volume: asNumber(item.volume),
          score: asNumber(item.value) ?? 0,
          confidence: asNumber(item.confidence) ?? 0,
          signal: item.direction === "BULLISH" ? "BULLISH" : item.direction === "BEARISH" ? "BEARISH" : "NEUTRAL",
        })));
        setLoadState("ready");
      } catch (error) {
        if ((error as Error).name !== "AbortError") setLoadState("error");
      }
    }

    void loadRanking();
    return () => controller.abort();
  }, []);

  const rows = useMemo(() => assets.filter((asset) => {
    const matchesQuery = `${asset.symbol} ${asset.name}`.toLowerCase().includes(query.toLowerCase());
    const matchesTab = tab === "All signals" || (tab === "High conviction" ? asset.confidence >= 0.85 : asset.signal === tab.toUpperCase());
    return matchesQuery && matchesTab;
  }).sort((a, b) => ascending ? a.score - b.score : b.score - a.score), [ascending, assets, query, tab]);

  const emptyMessage = loadState === "loading"
    ? "Loading calibrated ranking…"
    : loadState === "error"
      ? "API unavailable. Check the HAWK SCANNER API health endpoint."
      : rows.length === 0 && !query && tab === "All signals"
        ? "The first public evidence window is being collected. The ranking will appear after dynamic calibration."
        : "No assets match the active filters.";

  return <section className="panel overflow-hidden">
    <div className="flex flex-col gap-4 border-b border-white/[.07] p-5 lg:flex-row lg:items-center lg:justify-between">
      <div><h2 className="text-base font-semibold">Top Ranking</h2><p className="mt-1 text-xs text-muted-foreground">Assets ranked by the latest calibrated Hawk Score</p></div>
      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-[180px] flex-1 sm:min-w-[220px]"><Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search asset..." className="pl-9" /></div>
        <Button variant="outline" size="default"><Filter className="h-4 w-4" />Filters</Button>
      </div>
    </div>
    <div className="flex gap-1 overflow-x-auto border-b border-white/[.07] px-5 pt-2">{tabs.map((item) => <button key={item} onClick={() => setTab(item)} className={cn("whitespace-nowrap border-b-2 px-3 py-2.5 text-xs font-medium transition-colors", tab === item ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground")}>{item}</button>)}</div>
    <div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left text-sm">
      <thead className="bg-white/[.018] text-[10px] uppercase tracking-[.12em] text-muted-foreground"><tr><th className="w-12 px-5 py-3 font-medium">#</th><th className="font-medium">Asset</th><th className="font-medium">Price</th><th className="font-medium">24h</th><th className="font-medium">Volume</th><th className="font-medium"><button onClick={() => setAscending(!ascending)} className="flex items-center gap-1 hover:text-foreground">Score <ArrowDownUp className="h-3 w-3" /></button></th><th className="font-medium">Signal</th><th className="px-5" /></tr></thead>
      <tbody className="divide-y divide-white/[.055]">{rows.map((asset) => <tr key={asset.coinId} className="group transition-colors hover:bg-white/[.025]"><td className="number px-5 py-3.5 text-xs text-muted-foreground">{asset.rank.toString().padStart(2, "0")}</td><td><div className="flex items-center gap-2.5"><div className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-slate-700 to-slate-900 text-[10px] font-bold text-slate-100">{asset.symbol.slice(0, 2)}</div><div><p className="font-medium">{asset.symbol}<span className="ml-1.5 text-xs font-normal text-muted-foreground">{asset.name}</span></p></div></div></td><td className="number font-medium">{asset.price === null ? "—" : `$${asset.price.toLocaleString("en-US", { maximumFractionDigits: asset.price < 1 ? 4 : 2 })}`}</td><td className="number text-muted-foreground">—</td><td className="number text-muted-foreground">{asset.volume === null ? "—" : `$${compactCurrency(asset.volume)}`}</td><td><div className="flex items-center gap-2"><div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted"><div className={cn("h-full rounded-full", asset.score > 75 ? "bg-emerald-400" : asset.score > 55 ? "bg-amber-400" : "bg-rose-400")} style={{ width: `${asset.score}%` }} /></div><span className="number font-medium">{asset.score.toFixed(1)}</span></div></td><td><SignalBadge signal={asset.signal} /></td><td className="px-5"><Button variant="ghost" size="icon" className="h-7 w-7 opacity-0 group-hover:opacity-100"><Star className="h-3.5 w-3.5" /></Button></td></tr>)}{rows.length === 0 && <tr><td colSpan={8} className="p-10 text-center text-sm text-muted-foreground">{emptyMessage}</td></tr>}</tbody>
    </table></div>
    <div className="flex items-center justify-between border-t border-white/[.07] px-5 py-3 text-xs text-muted-foreground"><span>Showing {rows.length} of {assets.length} ranked assets</span><button className="flex items-center gap-1 text-primary hover:text-primary/80">View full scanner <ChevronDown className="h-3 w-3 -rotate-90" /></button></div>
  </section>;
}
