import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { heatmapAssets } from "@/lib/demo-data";

function backgroundFor(change: number) { const alpha = Math.min(Math.abs(change) / 18, 0.56) + 0.1; return change > 0 ? `rgba(16, 185, 129, ${alpha})` : `rgba(244, 63, 94, ${alpha})`; }

export function MarketHeatmap() {
  return <Card><CardHeader><div><CardTitle>Market Heatmap</CardTitle><p className="mt-1 text-xs text-muted-foreground">24h performance · weighted by liquidity</p></div><span className="text-xs text-primary">View all</span></CardHeader><CardContent><div className="grid grid-cols-3 gap-1.5 sm:grid-cols-4">{heatmapAssets.map(([symbol, change], index) => <div key={symbol} style={{ background: backgroundFor(change) }} className={`flex min-h-16 flex-col justify-between rounded-lg p-2.5 ${index === 0 ? "col-span-2 row-span-2 min-h-32" : ""}`}><span className={index === 0 ? "text-lg font-semibold" : "text-xs font-semibold"}>{symbol}</span><span className={index === 0 ? "text-base font-medium" : "text-[11px] font-medium"}>{change > 0 ? "+" : ""}{change.toFixed(1)}%</span></div>)}</div><div className="mt-4 flex items-center justify-between text-[10px] text-muted-foreground"><span>Bearish</span><div className="h-1.5 w-28 rounded-full bg-gradient-to-r from-rose-500 via-slate-500 to-emerald-500" /><span>Bullish</span></div></CardContent></Card>;
}
