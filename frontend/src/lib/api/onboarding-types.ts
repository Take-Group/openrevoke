// First steps of a new installation (tag "onboarding" in docs/openapi.json): the /welcome
// questions and the dashboard checklist. Separate from types.ts, which is past the line limit.

import type { DateTimeString } from "@/lib/api/types";

export type PeopleImport = "google_workspace" | "microsoft_365" | "csv" | "manual";
export type ChatPlatform = "slack" | "teams" | "none";
export type PasswordManager = "1password" | "bitwarden" | "other" | "none";

export interface OnboardingChoices {
  people_import?: PeopleImport | null;
  chat_platform?: ChatPlatform | null;
  password_manager?: PasswordManager | null;
}

export interface ChecklistItem {
  key: "people" | "chat" | "apps";
  title: string;
  description: string;
  href: string | null;
  action: string | null;
  done: boolean;
  /** False when Open Revoke cannot do the chosen option yet (Microsoft 365, Teams). */
  supported: boolean;
}

export interface OnboardingOut {
  people_import: PeopleImport | null;
  chat_platform: ChatPlatform | null;
  password_manager: PasswordManager | null;
  /** Every /welcome question has an answer. */
  answered: boolean;
  dismissed_at: DateTimeString | null;
  items: ChecklistItem[];
  completed: number;
}
