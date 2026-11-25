import { CopyButton } from "@/components/common/copy-button";
import { cn } from "@/lib/utils";

/** A command or a config snippet to paste elsewhere: monospace, kept as written, with a copy button. */
export function CodeBlock({ code, label, className }: { code: string; label?: string; className?: string }) {
  return (
    <div className={cn("relative min-w-0 rounded-lg border bg-subtle", className)}>
      <pre className="overflow-x-auto py-2.5 pr-10 pl-3 font-mono text-xs leading-relaxed whitespace-pre select-all">{code}</pre>
      <CopyButton value={code} label={label ? `Copy ${label}` : "Copy"} className="absolute top-1.5 right-1.5" />
    </div>
  );
}
