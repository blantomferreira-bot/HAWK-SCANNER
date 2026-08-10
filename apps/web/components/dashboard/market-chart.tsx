import { Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function MarketChart() {
  return <Card className="col-span-1 xl:col-span-2">
    <CardHeader><div><CardTitle>Índice de momentum</CardTitle><p className="mt-1 text-xs text-muted-foreground">Série consolidada de Hawk Score</p></div></CardHeader>
    <CardContent className="grid h-[275px] place-items-center pb-4"><div className="max-w-sm text-center"><span className="mx-auto grid h-11 w-11 place-items-center rounded-full border border-primary/20 bg-primary/10"><Activity className="h-5 w-5 text-primary" /></span><p className="mt-4 text-sm font-medium">Gráfico em preparação</p><p className="mt-2 text-xs leading-relaxed text-muted-foreground">A série será exibida quando houver histórico de scores suficiente. Não são mostrados dados de demonstração.</p></div></CardContent>
  </Card>;
}
