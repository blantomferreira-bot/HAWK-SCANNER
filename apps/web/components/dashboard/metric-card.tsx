import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function MetricCard({ title, value, delta, icon: Icon, detail }: { title: string; value: string; delta: number; icon: LucideIcon; detail: string }) {
  const positive = delta >= 0;
  return <Card className="relative overflow-hidden"><div className="absolute -right-5 -top-5 h-20 w-20 rounded-full bg-primary/5 blur-2xl" /><CardHeader><CardTitle>{title}</CardTitle><Icon className="h-4 w-4 text-muted-foreground" /></CardHeader><CardContent><p className="number text-2xl font-semibold tracking-tight">{value}</p><div className="mt-2 flex items-center gap-2 text-xs"><span className={positive ? "flex items-center text-emerald-400" : "flex items-center text-rose-400"}>{positive ? <ArrowUpRight className="mr-0.5 h-3.5 w-3.5" /> : <ArrowDownRight className="mr-0.5 h-3.5 w-3.5" />}{Math.abs(delta).toFixed(1)}%</span><span className="text-muted-foreground">{detail}</span></div></CardContent></Card>;
}
