"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MoreHorizontal } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { equityCurve } from "@/lib/demo-data";

export function MarketChart() {
  return <Card className="col-span-1 xl:col-span-2"><CardHeader><div><CardTitle>Signal Momentum Index</CardTitle><p className="mt-1 text-xs text-muted-foreground">Aggregated probability of expansion · 24h</p></div><div className="flex items-center gap-2"><div className="hidden rounded-lg bg-muted p-1 sm:flex">{["1H", "4H", "1D"].map((item, index) => <button key={item} className={`rounded-md px-2 py-1 text-[11px] ${index === 2 ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"}`}>{item}</button>)}</div><Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button></div></CardHeader><CardContent className="h-[275px] pb-4"><ResponsiveContainer width="100%" height="100%"><AreaChart data={equityCurve} margin={{ top: 15, right: 0, left: -22, bottom: 0 }}><defs><linearGradient id="signalFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#28d69c" stopOpacity={0.3} /><stop offset="95%" stopColor="#28d69c" stopOpacity={0} /></linearGradient></defs><XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: "#77839a", fontSize: 11 }} minTickGap={25} /><YAxis domain={[25, 110]} axisLine={false} tickLine={false} tick={{ fill: "#77839a", fontSize: 11 }} /><Tooltip contentStyle={{ background: "#111827", border: "1px solid #263246", borderRadius: "8px" }} labelStyle={{ color: "#94a3b8" }} itemStyle={{ color: "#e2e8f0" }} formatter={(value: number) => [`${value.toFixed(1)} / 100`, "Signal"]} /><Area type="monotone" dataKey="value" stroke="#28d69c" strokeWidth={2.4} fill="url(#signalFill)" /></AreaChart></ResponsiveContainer></CardContent></Card>;
}
