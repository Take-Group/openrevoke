/** Types of access requests (/api/access-requests), from docs/openapi.json. */

import type { ActionStatus, AppRef, DateTimeString, PersonRef, Uuid } from "@/lib/api/types";

export type AccessRequestStatus =
  | "pending_manager"
  | "pending_admin"
  | "approved"
  | "done"
  | "failed"
  | "rejected"
  | "cancelled";

export interface AccessRequestOut {
  id: Uuid;
  person: PersonRef;
  app: AppRef;
  action_id: Uuid | null;
  action_status: ActionStatus | null;
  /** slack: asked the Slack agent; panel: asked on My access. */
  channel: "slack" | "panel";
  status: AccessRequestStatus;
  message: string | null;
  created_at: DateTimeString;
  closed_at: DateTimeString | null;
  notified_at: DateTimeString | null;
}

export interface AccessRequestPage {
  items: AccessRequestOut[];
  total: number;
}
