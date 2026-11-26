"use client";

import { BotIcon, CheckIcon, MessageSquareIcon, ShieldCheckIcon, XIcon } from "lucide-react";

import { DetailList, type DetailRow } from "@/components/common/detail-list";
import { RecordLink } from "@/components/common/links";
import { Panel } from "@/components/common/panel";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge, type Tone } from "@/components/common/status-badge";
import { formatMoney, formatWhen, fullName, humanize } from "@/lib/format";
import type {
  AccessRequestDecisionOut,
  AccessRequestDetail,
  AccessRequestOut,
  AccessRequestStatus,
  RequestFallbackReason,
} from "@/lib/api/access-request-types";
import type { RequestPolicy } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const STATUS: Record<AccessRequestStatus, { label: string; tone: Tone }> = {
  pending_manager: { label: "Waiting for manager", tone: "warning" },
  pending_admin: { label: "Waiting for admin", tone: "warning" },
  approved: { label: "Approved", tone: "info" },
  done: { label: "Done", tone: "success" },
  failed: { label: "Failed", tone: "danger" },
  rejected: { label: "Rejected", tone: "danger" },
  cancelled: { label: "Cancelled", tone: "neutral" },
};

export const FALLBACK_TEXT: Record<RequestFallbackReason, string> = {
  no_manager: "No manager is set",
  manager_left: "The manager has left",
  manager_no_access: "The manager has no panel account and no Slack",
  manager_is_requester: "The person is their own manager",
};

export const POLICY_TEXT: Record<RequestPolicy, string> = {
  off: "Not available on request",
  automatic: "Approved automatically",
  manager: "The manager approves",
  manager_then_admin: "The manager, then an admin approves",
  admin: "An admin approves",
};

/** Status of an access request with the panel's wording ("Waiting for manager"). */
export function RequestStatusBadge({ status }: { status: AccessRequestStatus }) {
  const { label, tone } = STATUS[status];
  return <StatusBadge status={status} label={label} tone={tone} />;
}

/** Who decides next: the manager by name, or an admin (with the reason when the manager was skipped). */
export function waitingText(request: Pick<AccessRequestOut, "waiting_for" | "approver" | "fallback_reason">): string {
  if (request.waiting_for === "manager") return request.approver ? fullName(request.approver) : "Manager";
  if (request.waiting_for === "admin") {
    return request.fallback_reason ? `Admin (${FALLBACK_TEXT[request.fallback_reason].toLowerCase()})` : "Admin";
  }
  return "—";
}

function decisionTitle(decision: AccessRequestDecisionOut): string {
  const verb = decision.decision === "approved" ? "approved" : "rejected";
  if (decision.via === "automatic") return `${decision.step === "manager" ? "Manager step" : "Request"} ${verb} automatically`;
  if (decision.override) return `Admin ${verb} for the manager`;
  return `${decision.step === "manager" ? "Manager" : "Admin"} ${verb}`;
}

function DecisionIcon({ decision }: { decision: AccessRequestDecisionOut }) {
  const Icon = decision.via === "automatic" ? BotIcon : decision.decision === "approved" ? CheckIcon : XIcon;
  return (
    <span
      className={cn(
        "flex size-6 shrink-0 items-center justify-center rounded-full border bg-background",
        decision.decision === "approved" ? "text-success" : "text-destructive",
      )}
    >
      <Icon className="size-3.5" />
    </span>
  );
}

function TimelineItem({ icon, title, meta, children }: { icon: React.ReactNode; title: string; meta: React.ReactNode; children?: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      {icon}
      <div className="min-w-0 flex-1 pb-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{meta}</p>
        {children}
      </div>
    </li>
  );
}

function plainIcon(Icon: typeof MessageSquareIcon) {
  return (
    <span className="flex size-6 shrink-0 items-center justify-center rounded-full border bg-background text-muted-foreground">
      <Icon className="size-3.5" />
    </span>
  );
}

/** Oldest first: the request, every decision (who, when, via, comment) and the action's end. */
export function DecisionTimeline({ request }: { request: AccessRequestDetail }) {
  const action = request.action;
  return (
    <Panel title="Timeline" meta={request.decisions.length || undefined}>
      <ol className="flex flex-col gap-4 p-4">
        <TimelineItem
          icon={plainIcon(MessageSquareIcon)}
          title={request.on_behalf ? "Requested by the manager" : "Requested"}
          meta={`${formatWhen(request.created_at)} · ${request.requested_by ?? "unknown"} · ${request.channel === "slack" ? "Slack" : "panel or API"}`}
        />
        {request.decisions.map((decision) => (
          <TimelineItem
            key={decision.id}
            icon={<DecisionIcon decision={decision} />}
            title={decisionTitle(decision)}
            meta={`${formatWhen(decision.decided_at)} · ${decision.decided_by} · via ${decision.via}`}
          >
            {decision.comment && <p className="mt-1 text-sm text-muted-foreground">“{decision.comment}”</p>}
          </TimelineItem>
        ))}
        {request.fallback_reason && (
          <TimelineItem
            icon={plainIcon(ShieldCheckIcon)}
            title="Sent to an admin"
            meta={FALLBACK_TEXT[request.fallback_reason]}
          />
        )}
        {action && (action.status === "done" || action.status === "failed" || action.status === "cancelled") && (
          <TimelineItem
            icon={plainIcon(action.status === "done" ? CheckIcon : XIcon)}
            title={`Action ${humanize(action.status).toLowerCase()}`}
            meta={formatWhen(action.finished_at)}
          >
            {action.error && <p className="mt-1 text-sm text-destructive">{action.error}</p>}
          </TimelineItem>
        )}
      </ol>
    </Panel>
  );
}

/** The facts of a request as label and value rows; `admin` links the person and the app. */
export function RequestFacts({ request, admin }: { request: AccessRequestDetail; admin?: boolean }) {
  const rows: DetailRow[] = [
    [
      "Person",
      admin ? <RecordLink href={`/people/${request.person.person_id}`}>{fullName(request.person)}</RecordLink> : fullName(request.person),
    ],
    ["E-mail", request.person.primary_email],
    ["App", admin ? <RecordLink href={`/apps/${request.app.app_id}`}>{request.app.name}</RecordLink> : request.app.name],
    ["Role", request.role ?? "Default"],
    ["Why", request.justification ?? request.message ?? "—"],
    ["Seat per month", formatMoney(request.seat_monthly_cost)],
    ["Who approves", POLICY_TEXT[request.policy]],
    ["Status", <RequestStatusBadge key="status" status={request.status} />],
    ["Waiting for", waitingText(request)],
    ["Asked", <RelativeTime key="asked" value={request.created_at} />],
  ];
  if (request.rejection_comment) rows.push(["Rejection comment", request.rejection_comment]);
  if (request.action?.approved_by) rows.push(["Action approved by", request.action.approved_by]);
  return <DetailList rows={rows} />;
}
