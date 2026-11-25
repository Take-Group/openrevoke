import { CircleSlashIcon, ConstructionIcon, type LucideIcon } from "lucide-react";

import { STRINGS_BAND, Strings } from "@/components/common/strings";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title: string;
  /** One short muted line at most. */
  description?: React.ReactNode;
  icon?: LucideIcon;
  action?: React.ReactNode;
  className?: string;
}

/** Icon, one line and one action. */
export function EmptyState({ title, description, icon: Icon = CircleSlashIcon, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "relative isolate flex flex-col items-center justify-center gap-1.5 overflow-hidden px-6 py-12 text-center",
        className,
      )}
    >
      <Strings
        shape={STRINGS_BAND}
        count={12}
        intensity={0.16}
        className="-z-10 mask-[radial-gradient(ellipse_at_center,transparent_22%,black_65%)]"
      />
      <Icon className="mb-1.5 size-5 text-muted-foreground/70" strokeWidth={1.75} />
      <p className="text-sm font-medium">{title}</p>
      {description && <div className="max-w-sm text-sm text-muted-foreground">{description}</div>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

/** For endpoints that answer 501: the backend builds them in a later stage. */
export function NotAvailable({ what, className }: { what: string; className?: string }) {
  return <EmptyState icon={ConstructionIcon} title={`${what} is not available yet`} className={className} />;
}
