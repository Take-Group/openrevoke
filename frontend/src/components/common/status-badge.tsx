import { Badge } from "@/components/ui/badge";
import { humanize } from "@/lib/format";
import { cn } from "@/lib/utils";

export type Tone = "success" | "warning" | "danger" | "info" | "neutral";

/**
 * Dot colour of each tone. Text stays neutral, so both themes keep their contrast.
 * Three signal colours only (green, amber, red); "info" (in progress, invited) is ink.
 */
export const TONE_DOT: Record<Tone, string> = {
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-destructive",
  info: "bg-foreground/70",
  neutral: "bg-muted-foreground/40",
};

/** Text colour for a number or icon that needs attention. */
export const TONE_TEXT: Record<Tone, string> = {
  success: "text-success",
  warning: "text-warning",
  danger: "text-destructive",
  info: "text-foreground",
  neutral: "text-muted-foreground",
};

// One table for every status-like enum of the API. Unknown values are neutral.
const TONES: Record<string, Tone> = {
  // person
  active: "success",
  left: "neutral",
  // account
  invited: "info",
  suspended: "warning",
  removed: "neutral",
  // connection and sync run
  ok: "success",
  needs_login: "warning",
  error: "danger",
  never_synced: "neutral",
  running: "info",
  failed: "danger",
  // action
  pending_approval: "warning",
  approved: "info",
  verifying: "info",
  done: "success",
  cancelled: "neutral",
  // Slack agent and access requests
  connected: "success",
  connecting: "info",
  not_configured: "neutral",
  disabled: "neutral",
  open: "warning",
  // My access requests
  waiting_for_approval: "warning",
  in_progress: "info",
  // panel user (self sign-up)
  pending: "warning",
  // alert severity
  critical: "danger",
  warning: "warning",
};

const LABELS: Record<string, string> = {
  ok: "OK",
  needs_login: "Needs login",
  pending_approval: "Pending",
  not_configured: "Not set up",
  waiting_for_approval: "Waiting for approval",
  in_progress: "In progress",
  pending: "Waiting for approval",
};

/** States that are still moving get a pulsing dot. */
const PULSING = new Set(["running", "verifying", "approved", "connecting", "in_progress"]);

export function toneOf(status: string): Tone {
  return TONES[status] ?? "neutral";
}

export function StatusDot({ tone, pulse, className }: { tone: Tone; pulse?: boolean; className?: string }) {
  return (
    <span className={cn("relative inline-flex size-1.5 shrink-0 rounded-full", TONE_DOT[tone], className)}>
      {pulse && <span className={cn("absolute inset-0 animate-ping rounded-full opacity-60", TONE_DOT[tone])} />}
    </span>
  );
}

interface StatusBadgeProps {
  status: string | null | undefined;
  /** Text instead of the humanized status. */
  label?: string;
  /** Tone instead of the one from the status table. */
  tone?: Tone;
  className?: string;
}

export function StatusBadge({ status, label, tone, className }: StatusBadgeProps) {
  if (!status) return <span className="text-muted-foreground">—</span>;
  return (
    <Badge variant="outline" className={cn("h-5.5 gap-1.5 rounded-full pr-2 pl-1.5 font-medium text-foreground/80", className)}>
      <StatusDot tone={tone ?? toneOf(status)} pulse={PULSING.has(status)} />
      {label ?? LABELS[status] ?? humanize(status)}
    </Badge>
  );
}

const CONNECTION_LABELS: Record<string, string> = {
  ok: "Connected",
  needs_login: "Needs login",
  error: "Error",
  never_synced: "Never synced",
};

/** Connection state of an app; "Not connected" when there is none. */
export function ConnectionBadge({ status, className }: { status: string | null | undefined; className?: string }) {
  if (!status) return <StatusBadge status="none" label="Not connected" tone="neutral" className={className} />;
  return <StatusBadge status={status} label={CONNECTION_LABELS[status]} className={className} />;
}

/** Plain outlined badge for non-status values (kind, role, reason). */
export function TagBadge({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <Badge variant="outline" className={cn("h-5.5 px-1.5 font-normal text-muted-foreground", className)}>
      {children}
    </Badge>
  );
}
