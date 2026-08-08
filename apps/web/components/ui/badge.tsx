import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold", { variants: { variant: { default: "bg-primary/15 text-primary", bullish: "bg-emerald-500/15 text-emerald-400", bearish: "bg-rose-500/15 text-rose-400", neutral: "bg-slate-500/15 text-slate-300" } }, defaultVariants: { variant: "default" } });
export function Badge({ className, variant, ...props }: React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof badgeVariants>) { return <div className={cn(badgeVariants({ variant }), className)} {...props} />; }
