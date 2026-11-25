import { HandIcon, PauseCircleIcon, ZapIcon, type LucideIcon } from "lucide-react";

import { Hint } from "@/components/common/info-tip";
import type { WriteMode } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { WRITE_MODE_LABEL, writeModeHint } from "@/lib/write-mode";

const STYLE: Record<WriteMode, { icon: LucideIcon; className: string }> = {
  automatic: { icon: ZapIcon, className: "text-success" },
  writes_disabled: { icon: PauseCircleIcon, className: "text-warning" },
  manual: { icon: HandIcon, className: "text-muted-foreground" },
};

/** What a write does for this app (automatic, writes off, manual task); details in the tooltip. */
export function WriteModeBadge({
  mode,
  what,
  className,
}: {
  mode: WriteMode;
  what: "create" | "remove" | "suspend";
  className?: string;
}) {
  const { icon: Icon, className: tone } = STYLE[mode];
  return (
    <Hint label={writeModeHint(mode, what)}>
      <span className={cn("inline-flex items-center gap-1 text-xs font-medium whitespace-nowrap", tone, className)}>
        <Icon className="size-3.5" />
        {WRITE_MODE_LABEL[mode]}
      </span>
    </Hint>
  );
}

/** Badge and the hint as one muted line, for dialogs where the outcome matters. */
export function WriteModeLine({ mode, what }: { mode: WriteMode; what: "create" | "remove" | "suspend" }) {
  return (
    <p className="flex items-center gap-2 rounded-lg border bg-subtle px-3 py-2 text-xs text-muted-foreground">
      <WriteModeBadge mode={mode} what={what} />
      <span className="min-w-0">{writeModeHint(mode, what)}</span>
    </p>
  );
}
