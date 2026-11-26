// Access profile types (tag "access-profiles" in docs/openapi.json). Separate from types.ts, which is
// near the 600-line limit. Names match `components.schemas` in the contract.

import type {
  AccountRef,
  ActionOut,
  AppRef,
  DateTimeString,
  MoneyAmount,
  OnboardSkipped,
  PersonRef,
  Uuid,
  WriteMode,
} from "@/lib/api/types";

export interface AccessProfileAppIn {
  app_id: Uuid;
  role?: string | null;
}

export interface AccessProfileCreate {
  name: string;
  description?: string | null;
  auto_approve_requests?: boolean;
  apps?: AccessProfileAppIn[];
}

/** Only the fields present change; `apps` replaces the list. */
export type AccessProfileUpdate = Partial<AccessProfileCreate>;

export interface AccessProfileAppOut {
  app: AppRef;
  logo_url: string | null;
  role: string | null;
  /** What one person adds per month (per-seat apps only). */
  seat_price: MoneyAmount | null;
  seat_price_converted: MoneyAmount | null;
}

export interface AccessProfileOut {
  id: Uuid;
  name: string;
  description: string | null;
  auto_approve_requests: boolean;
  apps: AccessProfileAppOut[];
  member_count: number;
  /** Active members who lack an app of this profile. */
  members_missing_access: number;
  cost_per_person: MoneyAmount[];
  cost_per_person_total: MoneyAmount | null;
  created_at: DateTimeString;
  updated_at: DateTimeString;
}

export interface AccessProfileList {
  items: AccessProfileOut[];
  total: number;
}

export interface ProfileRef {
  profile_id: Uuid;
  name: string;
}

export interface AppRoleSuggestions {
  app_id: Uuid;
  roles: string[];
}

export interface AppRoleSuggestionList {
  items: AppRoleSuggestions[];
}

export interface MissingAccess {
  app: AppRef;
  logo_url: string | null;
  role: string | null;
  profiles: string[];
}

export interface ExtraAccess {
  account: AccountRef;
  app: AppRef;
  role: string | null;
}

export interface RoleMismatch {
  account: AccountRef;
  app: AppRef;
  role: string;
  expected_role: string;
  profiles: string[];
}

export interface AccessDrift {
  missing: MissingAccess[];
  /** Accounts in apps outside every profile; empty when the person has no profile. */
  extra: ExtraAccess[];
  role_mismatch: RoleMismatch[];
}

export interface PersonAccessDrift extends AccessDrift {
  person: PersonRef;
  profiles: ProfileRef[];
}

export interface PersonAccessProfileOut {
  profile: ProfileRef;
  description: string | null;
  auto_approve_requests: boolean;
  apps: AccessProfileAppOut[];
  assigned_at: DateTimeString;
  assigned_by: string | null;
}

export interface PersonAccessProfileList {
  items: PersonAccessProfileOut[];
}

export interface AccessProfileMember extends AccessDrift {
  person: PersonRef;
  assigned_at: DateTimeString;
  assigned_by: string | null;
}

export interface AccessProfileMemberList {
  items: AccessProfileMember[];
  total: number;
}

export interface ProfileAssign {
  profile_ids: Uuid[];
  dry_run?: boolean;
  /** False: only assign, no onboarding actions. */
  create_actions?: boolean;
}

export interface MembersAssign {
  person_ids: Uuid[];
  dry_run?: boolean;
}

export interface PlannedAction {
  app: AppRef;
  logo_url: string | null;
  role: string | null;
  write_mode: WriteMode;
  profiles: string[];
  monthly_cost: MoneyAmount | null;
  monthly_cost_converted: MoneyAmount | null;
}

export interface ProfileAssignResult {
  person: PersonRef;
  dry_run: boolean;
  assigned: ProfileRef[];
  planned: PlannedAction[];
  skipped: OnboardSkipped[];
  warnings: string[];
  monthly_cost: MoneyAmount[];
  monthly_cost_total: MoneyAmount | null;
  batch_id: Uuid | null;
  actions: ActionOut[];
}

export interface SkippedPerson {
  person: PersonRef;
  reason: string;
}

export interface MembersAssignResult {
  dry_run: boolean;
  items: ProfileAssignResult[];
  skipped_people: SkippedPerson[];
  monthly_cost: MoneyAmount[];
  monthly_cost_total: MoneyAmount | null;
}

export interface SuggestedRemoval {
  account: AccountRef;
  app: AppRef;
  role: string | null;
  write_mode: WriteMode;
}

export interface ProfileUnassignResult {
  person: PersonRef;
  profile: ProfileRef;
  suggested_removals: SuggestedRemoval[];
}
