// `/api/me`: the signed-in user's own access ("My access") and their team, from docs/openapi.json.

import type { AccessRequestStatus, RequestFallbackReason, WaitingFor } from "@/lib/api/access-request-types";
import type { AccountStatus, AppRef, DateTimeString, PersonRef, RequestPolicy, Uuid } from "@/lib/api/types";

export interface MyAccount {
  account_id: Uuid;
  app: AppRef;
  email: string | null;
  username: string | null;
  /** Role in the app, as the app reports it. */
  role: string | null;
  status: AccountStatus;
  first_seen_at: DateTimeString;
  last_seen_at: DateTimeString | null;
}

export interface MyRequest {
  request_id: Uuid;
  app: AppRef;
  status: AccessRequestStatus;
  waiting_for: WaitingFor | null;
  /** The manager the request waits for (or waited for). */
  approver: PersonRef | null;
  fallback_reason: RequestFallbackReason | null;
  justification: string | null;
  role: string | null;
  rejection_comment: string | null;
  requested_by: string | null;
  on_behalf: boolean;
  created_at: DateTimeString;
  closed_at: DateTimeString | null;
}

export interface RequestableApp {
  app: AppRef;
  policy: RequestPolicy;
  /** Roles of existing accounts in the app, as suggestions. */
  roles: string[];
}

export interface MyAccess {
  /** The person with the user's e-mail; null when the company does not list them. */
  person: PersonRef | null;
  accounts: MyAccount[];
  /** Newest first, at most 50. */
  requests: MyRequest[];
  /** Policy not off, no account and no open request yet. */
  requestable_apps: RequestableApp[];
}

export interface MyAccessRequestCreate {
  app_id: Uuid;
  justification: string;
  role?: string | null;
  /** One of your reports; empty asks for yourself. */
  person_id?: Uuid | null;
}

export type RequestOutcome =
  | "in_progress"
  | "waiting_for_manager"
  | "waiting_for_approval"
  | "waiting_for_admin"
  | "already_has_account"
  | "already_requested"
  | "not_available";

export interface MyAccessRequestResult {
  outcome: RequestOutcome;
  app_name: string;
  /** waiting_for_manager: the manager's name; else why it waits for an admin. */
  note: string | null;
  request_id: Uuid | null;
}

export interface TeamMember {
  person: PersonRef;
  /** Apps where the person has an account. */
  apps: AppRef[];
  requestable_apps: RequestableApp[];
}

export interface MyTeam {
  reports: TeamMember[];
}
