import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export type NoticeTone = "danger" | "warning" | "success" | "info";

const TONE: Record<NoticeTone, { box: string; icon: string; Icon: LucideIcon }> = {
  danger: { box: "border-destructive/25 bg-destructive/[0.04]", icon: "text-destructive", Icon: TriangleAlertIcon },
  warning: { box: "border-warning/35 bg-warning/[0.07]", icon: "text-warning", Icon: TriangleAlertIcon },
  success: { box: "border-success/30 bg-success/[0.06]", icon: "text-success", Icon: CircleCheckIcon },
  info: { box: "bg-subtle", icon: "text-muted-foreground", Icon: InfoIcon },
};

interface NoticeProps {
  tone?: NoticeTone;
  /** Bold first line; `children` go under it. */
  title?: React.ReactNode;
  /** Button or link on the right. */
  action?: React.ReactNode;
  icon?: LucideIcon;
  className?: string;
  children?: React.ReactNode;
}

/**
 * The one alert box of the panel: an error, a warning, a success or a hint.
 * Text stays ink; only the icon and a light tint carry the tone.
 */
export function Notice({ tone = "info", title, action, icon, className, children }: NoticeProps) {
  const { box, icon: iconClass, Icon: ToneIcon } = TONE[tone];
  const Icon = icon ?? ToneIcon;
  return (
    <div
      role={tone === "danger" ? "alert" : undefined}
      className={cn("flex items-start gap-2.5 rounded-lg border px-3 py-2 text-sm text-foreground", box, className)}
    >
      <Icon className={cn("mt-0.5 size-4 shrink-0", iconClass)} />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5 break-words">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={cn(title && "text-muted-foreground")}>{children}</div>}
      </div>
      {action && <div className="shrink-0 self-center">{action}</div>}
    </div>
  );
}

/** An error message from the API or a failed check. */
export function InlineError({ message, className }: { message: React.ReactNode; className?: string }) {
  return (
    <Notice tone="danger" className={className}>
      {message}
    </Notice>
  );
}
