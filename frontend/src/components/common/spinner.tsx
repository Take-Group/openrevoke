import { Loader2Icon } from "lucide-react";

import { cn } from "@/lib/utils";

/** The one loading indicator. On a button that refreshes, spin its own icon instead. */
export function Spinner({ className }: { className?: string }) {
  return <Loader2Icon aria-label="Loading" className={cn("size-4 animate-spin text-muted-foreground", className)} />;
}
