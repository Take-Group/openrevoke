import { Hint } from "@/components/common/info-tip";
import { formatRelative, formatWhen } from "@/lib/format";
import { cn } from "@/lib/utils";

/** "5 min ago" with the exact date and time in a tooltip. */
export function RelativeTime({ value, className }: { value: string | null | undefined; className?: string }) {
  if (!value) return <span className={cn("text-muted-foreground", className)}>—</span>;
  return (
    <Hint label={formatWhen(value)}>
      <time dateTime={value} className={cn("whitespace-nowrap text-muted-foreground", className)}>
        {formatRelative(value)}
      </time>
    </Hint>
  );
}
