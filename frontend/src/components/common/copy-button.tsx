"use client";

import { useEffect, useState } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Copies `value` and shows a check mark for a moment. */
export function CopyButton({ value, label = "Copy", className }: { value: string; label?: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 1500);
    return () => clearTimeout(timer);
  }, [copied]);
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-xs"
      aria-label={label}
      title={label}
      className={className}
      onClick={() => {
        navigator.clipboard.writeText(value).then(
          () => setCopied(true),
          () => toast.error("Could not copy. Select the text and copy it by hand."),
        );
      }}
    >
      {copied ? <CheckIcon className="text-success" /> : <CopyIcon />}
    </Button>
  );
}

/**
 * A value to paste elsewhere (a link, a redirect URI, a secret, a 2FA key):
 * monospace text in a grey field with a copy button.
 */
export function CopyField({ value, label, className }: { value: string; label?: string; className?: string }) {
  return (
    <div className={cn("flex h-8 min-w-0 items-center gap-2 rounded-lg border bg-subtle pr-1 pl-2.5 font-mono text-xs", className)}>
      <span className="min-w-0 flex-1 truncate select-all">{value}</span>
      <CopyButton value={value} label={label ? `Copy ${label}` : "Copy"} />
    </div>
  );
}
