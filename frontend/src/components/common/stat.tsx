import { InfoTip } from "@/components/common/info-tip";
import { cn } from "@/lib/utils";

/** A strip of small facts under a detail header: label above, value below. */
export function StatStrip({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <dl
      className={cn(
        "mb-6 grid grid-cols-2 divide-x divide-y overflow-hidden rounded-lg border border-frame bg-card shadow-card sm:grid-cols-3 sm:divide-y-0 lg:flex lg:divide-y-0",
        className,
      )}
    >
      {children}
    </dl>
  );
}

/** One fact of a `StatStrip`. `icon` is accepted but not shown. */
export function Stat({
  label,
  info,
  children,
}: {
  label: string;
  /** Explanation behind an info icon next to the label. */
  info?: React.ReactNode;
  children: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-1 px-4 py-3">
      <dt className="flex items-center gap-1 text-xs text-muted-foreground">
        {label}
        {info && <InfoTip>{info}</InfoTip>}
      </dt>
      <dd className="truncate text-sm font-medium tabular-nums">{children}</dd>
    </div>
  );
}
