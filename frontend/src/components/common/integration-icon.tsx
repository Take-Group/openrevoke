import { GlobeIcon, KeyRoundIcon, PenLineIcon, PlugIcon, type LucideIcon } from "lucide-react";

import { Hint } from "@/components/common/info-tip";
import type { Integration } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export const INTEGRATION: Record<Integration, { icon: LucideIcon; label: string; hint: string }> = {
  api: { icon: PlugIcon, label: "API", hint: "API: accounts are read from the app's API" },
  scim: { icon: KeyRoundIcon, label: "SCIM", hint: "SCIM 2.0: accounts are read over SCIM" },
  browser: { icon: GlobeIcon, label: "Browser", hint: "Browser: accounts are read from the admin panel in the shared browser" },
  manual: { icon: PenLineIcon, label: "Manual", hint: "Manual: accounts are entered by hand" },
};

/** Integration type as an icon with a tooltip; `withLabel` adds the short name. */
export function IntegrationIcon({
  integration,
  withLabel,
  className,
}: {
  integration: Integration;
  withLabel?: boolean;
  className?: string;
}) {
  const { icon: Icon, label, hint } = INTEGRATION[integration];
  return (
    <Hint label={hint}>
      <span
        className={cn(
          "inline-flex items-center gap-1.5 text-muted-foreground",
          withLabel && "h-5.5 rounded-md border bg-background px-1.5 text-xs font-medium dark:bg-transparent",
          className,
        )}
        aria-label={label}
      >
        <Icon className="size-3.5" />
        {withLabel && label}
      </span>
    </Hint>
  );
}
