import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(({ className, type, ...props }, ref) => <input type={type} className={cn("flex h-9 w-full rounded-lg border border-input bg-muted/40 px-3 py-1 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring", className)} ref={ref} {...props} />);
Input.displayName = "Input";
