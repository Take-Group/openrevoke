import { InfoIcon } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/** Small info icon; the explanation shows on hover or focus. */
export function InfoTip({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <button
            type="button"
            aria-label="More information"
            className={cn("inline-flex text-muted-foreground hover:text-foreground", className)}
          />
        }
      >
        <InfoIcon className="size-3.5" />
      </TooltipTrigger>
      <TooltipContent className="max-w-72 text-left leading-relaxed">{children}</TooltipContent>
    </Tooltip>
  );
}

/** Any element with a tooltip. */
export function Hint({ label, children }: { label: React.ReactNode; children: React.ReactElement }) {
  return (
    <Tooltip>
      <TooltipTrigger render={children} />
      <TooltipContent className="max-w-72 text-left leading-relaxed">{label}</TooltipContent>
    </Tooltip>
  );
}
