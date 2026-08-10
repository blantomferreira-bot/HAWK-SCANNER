import { Grid3X3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function MarketHeatmap() {
  return <Card>
    <CardHeader><div><CardTitle>Heatmap de mercado</CardTitle><p className="mt-1 text-xs text-muted-foreground">Variações baseadas em dados armazenados</p></div></CardHeader>
    <CardContent className="grid h-[275px] place-items-center"><div className="max-w-[15rem] text-center"><span className="mx-auto grid h-11 w-11 place-items-center rounded-full border border-primary/20 bg-primary/10"><Grid3X3 className="h-5 w-5 text-primary" /></span><p className="mt-4 text-sm font-medium">Heatmap em preparação</p><p className="mt-2 text-xs leading-relaxed text-muted-foreground">Ele será ativado com variações reais de preço, após a formação do histórico.</p></div></CardContent>
  </Card>;
}
