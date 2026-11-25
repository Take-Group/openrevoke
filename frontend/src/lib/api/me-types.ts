// `/api/me`: the signed-in user's own access (the "My access" page), from docs/openapi.json.

import type { AccountStatus, AppRef, DateTimeString, PersonRef, Uuid } from "@/lib/api/types";

export type RequestState = "waiting_for_approval" | "in_progress" | "done" | "failed" | "cancelled";

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
  state: RequestState;
  message: string | null;
  created_at: DateTimeString;
}

export interface RequestableApp {
  app: AppRef;
  /** False: the account is created without waiting for an admin. */
  needs_approval: boolean;
}

export interface MyAccess {
  /** The person with the user's e-mail; null when the company does not list them. */
  person: PersonRef | null;
  accounts: MyAccount[];
  /** Newest first, at most 50. */
  requests: MyRequest[];
  /** Self-service on, no account and no open request yet. */
  requestable_apps: RequestableApp[];
}

export interface MyAccessRequestCreate {
  app_id: Uuid;
  message?: string | null;
}

export type RequestOutcome =
  | "in_progress"
  | "waiting_for_approval"
  | "waiting_for_admin"
  | "already_has_account"
  | "already_requested"
  | "not_available";

export interface MyAccessRequestResult {
  outcome: RequestOutcome;
  app_name: string;
  note: string | null;
}
