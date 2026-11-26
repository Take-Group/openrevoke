/** Types of access requests (/api/access-requests for admins, /api/me/approvals for managers), from docs/openapi.json. */

import type { ActionKind, ActionStatus, AppRef, DateTimeString, MoneyAmount, PersonRef, RequestPolicy, Uuid } from "@/lib/api/types";

export type AccessRequestStatus =
  | "pending_manager"
  | "pending_admin"
  | "approved"
  | "done"
  | "failed"
  | "rejected"
  | "cancelled";

export type WaitingFor = "manager" | "admin";

export type RequestFallbackReason = "no_manager" | "manager_left" | "manager_no_access" | "manager_is_requester";

export type DecisionStep = "manager" | "admin";
export type DecisionOutcome = "approved" | "rejected";
export type DecisionVia = "panel" | "slack" | "api" | "automatic";

export interface AccessRequestDecisionOut {
  id: Uuid;
  step: DecisionStep;
  decision: DecisionOutcome;
  /** E-mail of the panel user, "e-mail (Slack)", a token name or "Automatic (...)". */
  decided_by: string;
  decided_by_user_id: Uuid | null;
  via: DecisionVia;
  /** An admin decided for the manager. */
  override: boolean;
  comment: string | null;
  decided_at: DateTimeString;
}

export interface AccessRequestOut {
  id: Uuid;
  person: PersonRef;
  app: AppRef;
  action_id: Uuid | null;
  action_status: ActionStatus | null;
  /** slack: asked the Slack agent; panel: the panel or the API. */
  channel: "slack" | "panel";
  status: AccessRequestStatus;
  /** Who decides next; null when nobody (approved or closed). */
  waiting_for: WaitingFor | null;
  /** The manager the request waits for (or waited for). */
  approver: PersonRef | null;
  fallback_reason: RequestFallbackReason | null;
  justification: string | null;
  role: string | null;
  message: string | null;
  requested_by: string | null;
  /** The person's manager asked for them. */
  on_behalf: boolean;
  rejection_comment: string | null;
  created_at: DateTimeString;
  closed_at: DateTimeString | null;
  notified_at: DateTimeString | null;
}

export interface AccessRequestActionOut {
  id: Uuid;
  kind: ActionKind;
  status: ActionStatus;
  approved_by: string | null;
  approved_at: DateTimeString | null;
  finished_at: DateTimeString | null;
  error: string | null;
}

export interface AccessRequestDetail extends AccessRequestOut {
  policy: RequestPolicy;
  seat_monthly_cost: MoneyAmount | null;
  /** Oldest first. */
  decisions: AccessRequestDecisionOut[];
  action: AccessRequestActionOut | null;
}

export interface AccessRequestPage {
  items: AccessRequestOut[];
  total: number;
}

export interface AccessRequestDecisionCreate {
  /** Required to reject; shown to the person who asked. */
  comment?: string | null;
}

export interface MyApprovals extends AccessRequestPage {
  /** Requests waiting for the signed-in user's decision. */
  pending: number;
  /** Someone has the signed-in user as their manager. */
  has_reports: boolean;
}

export interface AccessRequestFilters {
  status?: AccessRequestStatus[];
  app_id?: Uuid;
  person_id?: Uuid;
  from?: string;
  to?: string;
  waiting_for?: WaitingFor;
}
