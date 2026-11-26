import type { AppBillingOut } from "@/lib/api/billing-types";
import type { RecipeFixOut } from "@/lib/api/recipe-fix-types";

// Types of the Open Revoke REST API, written by hand from docs/openapi.json.
//
// The backend generates docs/openapi.json (skills/backend/domain-model.md).
// After it changes, compare this file with a fresh generated copy:
//   cd frontend && bunx openapi-typescript ../docs/openapi.json -o /tmp/open-revoke-api.d.ts
// and update the shapes below. Names match `components.schemas` in the contract.

export type Uuid = string;
/** ISO 8601 date-time with offset. */
export type DateTimeString = string;

export interface Page<T> {
  items: T[];
  total: number;
}

export interface ErrorResponse {
  detail: string;
}

export interface MoneyAmount {
  currency: string;
  /** Two decimal places, e.g. "123.40". */
  amount: string;
}

// --- Enums -----------------------------------------------------------------

export type PersonStatus = "active" | "left";
/** human, or service: shared mailbox or technical account. */
export type PersonKind = "human" | "service";
/** auto: set by the import rules (a sync may change it); manual: set by an admin. */
export type PersonKindSource = "auto" | "manual";
/** Who set a person's manager: a people source (auto) or an admin, also by CSV import (manual). */
export type ManagerSource = "auto" | "manual";
export type Integration = "api" | "scim" | "browser" | "manual";
export type PricingModel = "per_seat" | "flat" | "free";
export type BillingPeriod = "monthly" | "yearly";
export type ConnectionStatus = "ok" | "needs_login" | "error" | "never_synced";
export type AccountStatus = "active" | "invited" | "suspended" | "removed";
export type AccountKind = "person" | "service" | "unknown";
export type MatchMethod = "email" | "alias" | "manual" | "none";
export type PersonLinkSource = "manual" | "csv" | "connection";
export type SyncRunStatus = "running" | "ok" | "failed" | "needs_login";
export type ActionKind = "create_account" | "delete_account" | "manual_task";
export type WriteKind = "create_account" | "delete_account";
export type ActionReason = "offboarding" | "onboarding" | "manual" | "self_service";
/** Requests through the Slack agent: refused, approved by an admin, or approved at once. */
/** Who approves when a person asks for an account in the app. */
export type RequestPolicy = "off" | "automatic" | "manager" | "manager_then_admin" | "admin";
export type ActionStatus =
  | "pending_approval"
  | "approved"
  | "running"
  | "verifying"
  | "done"
  | "failed"
  | "cancelled";
export type AlertKind =
  | "left_person_active_account"
  | "unassigned_accounts"
  | "connection_needs_login"
  | "connection_error"
  | "action_failed"
  | "person_inactive_in_source"
  | "discovered_sign_ins_at_risk"
  | "people_without_manager";
export type AlertSeverity = "critical" | "warning";
export type AlertEntityType = "account" | "app" | "connection" | "action" | "person" | "discovered_app";
export type ImportRowAction = "create" | "update" | "unchanged" | "error";
export type OffboardSkipReason = "service_account" | "action_open";
export type OnboardSkipReason = "has_account" | "action_open";
/** What a write to an app does: runs after approval, waits for "Allow writes", or becomes a manual task. */
export type WriteMode = "automatic" | "writes_disabled" | "manual";

// --- References ----------------------------------------------------------

export interface PersonRef {
  person_id: Uuid;
  first_name: string;
  last_name: string;
  primary_email: string;
  status: PersonStatus;
}

export interface AppRef {
  app_id: Uuid;
  name: string;
  slug: string;
}

export interface AccountRef {
  account_id: Uuid;
  email: string | null;
  username: string | null;
  display_name: string | null;
  status: AccountStatus;
}

// --- Dashboard -------------------------------------------------------------

export interface DashboardCounts {
  people_active: number;
  people_left: number;
  apps: number;
  accounts: number;
  seats: number;
  accounts_unassigned: number;
  connections_with_problems: number;
  actions_pending_approval: number;
  actions_failed: number;
}

export interface Alert {
  kind: AlertKind;
  severity: AlertSeverity;
  message: string;
  entity_type: AlertEntityType;
  entity_id: Uuid;
  app_id: Uuid | null;
  person_id: Uuid | null;
  count: number | null;
}

export interface Dashboard {
  counts: DashboardCounts;
  monthly_cost: MoneyAmount[];
  monthly_cost_total: MoneyAmount | null;
  exchange_rates: ExchangeRatesInfo | null;
  alerts: Alert[];
}

// --- People ----------------------------------------------------------------

export interface PersonListItem {
  id: Uuid;
  first_name: string;
  last_name: string;
  primary_email: string;
  employee_code: string | null;
  status: PersonStatus;
  left_at: DateTimeString | null;
  kind: PersonKind;
  kind_source: PersonKindSource;
  /** Why the rules made it a service account. */
  kind_reason: string | null;
  department: string | null;
  job_title: string | null;
  /** The person's manager; approves their access requests. */
  manager: PersonRef | null;
  /** auto: a people source sets it (a sync may change it); manual: an admin or a CSV import. */
  manager_source: ManagerSource;
  accounts_count: number;
  apps: AppRef[];
  monthly_cost: MoneyAmount[];
  /** All of monthly_cost in the organization currency; null when a currency has no rate. */
  monthly_cost_total: MoneyAmount | null;
  created_at: DateTimeString;
  updated_at: DateTimeString;
}

export interface PersonPage extends Page<PersonListItem> {
  /** Matches of the other filters per kind, for the filter tabs. */
  kind_counts: Record<PersonKind, number>;
}

export interface AliasOut {
  id: Uuid;
  email: string;
}

export interface PersonSourceOut {
  id: Uuid;
  source_type: PersonLinkSource;
  source_id: Uuid;
  source_name: string;
  external_id: string;
  is_active: boolean;
  last_seen_at: DateTimeString | null;
}

export interface AccountOut {
  id: Uuid;
  app_id: Uuid;
  connection_id: Uuid | null;
  external_id: string;
  email: string | null;
  username: string | null;
  display_name: string | null;
  role: string | null;
  status: AccountStatus;
  kind: AccountKind;
  match_method: MatchMethod;
  person: PersonRef | null;
  monthly_cost: MoneyAmount | null;
  monthly_cost_converted: MoneyAmount | null;
  first_seen_at: DateTimeString;
  last_seen_at: DateTimeString | null;
  removed_at: DateTimeString | null;
}

export interface PersonAccountOut extends AccountOut {
  app: AppRef;
}

export interface PersonDetail extends PersonListItem {
  notes: string | null;
  aliases: AliasOut[];
  sources: PersonSourceOut[];
  accounts: PersonAccountOut[];
  /** No accounts and no actions: DELETE /api/people/{id} is allowed. */
  can_delete: boolean;
  /** People whose manager is this person, active first. */
  reports: PersonRef[];
}

export interface PersonCreate {
  first_name: string;
  last_name: string;
  primary_email: string;
  employee_code?: string | null;
  notes?: string | null;
  aliases?: string[];
  manager_id?: Uuid | null;
  department?: string | null;
  job_title?: string | null;
}

export interface PersonUpdate {
  first_name?: string | null;
  last_name?: string | null;
  primary_email?: string | null;
  employee_code?: string | null;
  notes?: string | null;
  status?: PersonStatus | null;
  left_at?: DateTimeString | null;
  /** Replaces the whole alias list. */
  aliases?: string[] | null;
  /** Person or service account; an admin's choice is kept by syncs. */
  kind?: PersonKind | null;
  /** Manager set by hand (kept by syncs); null clears it. 400 on a loop. */
  manager_id?: Uuid | null;
  department?: string | null;
  job_title?: string | null;
}

export interface FieldChange {
  field: string;
  old: string | null;
  new: string | null;
}

export interface ImportRowResult {
  line: number;
  email: string | null;
  action: ImportRowAction;
  person_id: Uuid | null;
  changes: FieldChange[];
  errors: string[];
  /** create rows only: the new person's fields. */
  first_name?: string | null;
  last_name?: string | null;
  employee_code?: string | null;
  aliases?: string[];
  manager_email?: string | null;
  department?: string | null;
  job_title?: string | null;
}

export interface ImportResult {
  dry_run: boolean;
  created: number;
  updated: number;
  unchanged: number;
  failed: number;
  rows: ImportRowResult[];
}

// --- Apps ------------------------------------------------------------------

export interface PriceIn {
  /** Up to 10 digits and 2 decimals, e.g. "12.50". */
  amount: string;
  /** ISO 4217 code. */
  currency: string;
  billing_period?: BillingPeriod;
}

export interface PriceOut {
  amount: string;
  currency: string;
  billing_period: BillingPeriod;
}

export interface AppListItem {
  id: Uuid;
  name: string;
  slug: string;
  admin_url: string | null;
  integration: Integration;
  pricing_model: PricingModel;
  /** In the app's own currency. Null for free apps. */
  price: PriceOut | null;
  /** price in the organization currency; null for free apps and without a rate (show price). */
  price_converted: PriceOut | null;
  connector_key: string | null;
  connection_status: ConnectionStatus | null;
  last_synced_at: DateTimeString | null;
  active_seats: number;
  accounts_count: number;
  unassigned_count: number;
  monthly_cost: MoneyAmount | null;
  /** monthly_cost in the organization currency; null without a rate. */
  monthly_cost_converted: MoneyAmount | null;
  /** What "Add to app" does. */
  create_mode: WriteMode;
  /** What removing an account (offboarding, "Remove from app") does. */
  delete_mode: WriteMode;
  /** The connector suspends instead of deleting (Google Workspace): label "Suspend". */
  delete_suspends: boolean;
  request_policy: RequestPolicy;
  created_at: DateTimeString;
}

export interface ConnectionOut {
  id: Uuid;
  connector_key: string;
  config: Record<string, unknown>;
  secrets_set: boolean;
  /** Names of the stored secret fields. Values are never returned. */
  secret_fields_set: string[];
  is_people_source: boolean;
  writes_enabled: boolean;
  status: ConnectionStatus;
  last_synced_at: DateTimeString | null;
  last_error: string | null;
  created_at: DateTimeString;
}

export interface AppDetail extends AppListItem {
  notes: string | null;
  connection: ConnectionOut | null;
  /** Null when the connector does not read billing. */
  billing: AppBillingOut | null;
}

export interface AppCreate {
  name: string;
  slug?: string | null;
  admin_url?: string | null;
  integration?: Integration;
  pricing_model?: PricingModel;
  /** Required unless pricing_model is free, null when it is. */
  price?: PriceIn | null;
  notes?: string | null;
}

export type AppUpdate = Partial<{
  name: string | null;
  slug: string | null;
  admin_url: string | null;
  integration: Integration | null;
  pricing_model: PricingModel | null;
  price: PriceIn | null;
  notes: string | null;
  request_policy: RequestPolicy | null;
  /** true: take the price from the app's billing again. */
  price_from_app: boolean | null;
}>;

// --- Accounts --------------------------------------------------------------

export interface AccountCreate {
  email?: string | null;
  username?: string | null;
  display_name?: string | null;
  role?: string | null;
  status?: AccountStatus;
  kind?: AccountKind | null;
  person_id?: Uuid | null;
}

export interface AccountUpdate {
  /** Also null: a manual assignment that sync never overrides. */
  person_id?: Uuid | null;
  kind?: AccountKind | null;
  role?: string | null;
  status?: AccountStatus | null;
  display_name?: string | null;
}

// --- Connectors and connections -------------------------------------------

export interface ConnectorOut {
  key: string;
  display_name: string;
  integration: Integration;
  /** api_token, google_service_account, scim_token or browser_session. */
  auth_kind: string;
  /** list_accounts, create_account, delete_account, list_people. */
  capabilities: string[];
  /** JSON Schema of the connection form. */
  config_schema: Record<string, unknown>;
  secret_fields: string[];
  login_url: string | null;
  admin_url: string | null;
  /** delete_account suspends instead (Google Workspace). */
  delete_suspends: boolean;
}

export interface ConnectionUpsert {
  connector_key: string;
  config?: Record<string, unknown>;
  /** Null keeps the stored secrets, {} removes them. */
  secrets?: Record<string, string> | null;
  is_people_source?: boolean;
  writes_enabled?: boolean;
}

export interface ConnectionCheckResult {
  ok: boolean;
  status: ConnectionStatus;
  message: string | null;
}

export interface SyncRunOut {
  id: Uuid;
  connection_id: Uuid;
  started_at: DateTimeString;
  finished_at: DateTimeString | null;
  status: SyncRunStatus;
  accounts_seen: number;
  accounts_added: number;
  accounts_removed: number;
  error: string | null;
}

// --- Actions ---------------------------------------------------------------

export interface ActionPayload {
  operation?: WriteKind | null;
  email?: string | null;
  role?: string | null;
}

export interface ActionOut {
  id: Uuid;
  kind: ActionKind;
  status: ActionStatus;
  reason: ActionReason;
  batch_id: Uuid | null;
  person: PersonRef | null;
  app: AppRef;
  account: AccountRef | null;
  payload: ActionPayload;
  approved_at: DateTimeString | null;
  /** Who approved: panel user e-mail, "e-mail (Slack)", a token, or "Automatic (...)". */
  approved_by: string | null;
  /** Who asked for it; null for workflows and old actions. */
  created_by: string | null;
  started_at: DateTimeString | null;
  finished_at: DateTimeString | null;
  result: Record<string, unknown> | null;
  error: string | null;
  /** A one-time secret (temporary password) waits for reveal-secret. */
  has_secret_result: boolean;
  /** delete_account suspends instead of deleting (Google Workspace): label "Suspend". */
  suspends: boolean;
  /** A click recipe stopped: GET /api/actions/{id}/screenshot shows where. */
  has_screenshot: boolean;
  /** Recipe fixes the AI made during this action; a proposed one waits for an admin. */
  recipe_fixes: RecipeFixOut[];
  created_at: DateTimeString;
}

export interface ActionList extends Page<ActionOut> {
  /** Every status, counted with all filters except status. */
  counts: Record<ActionStatus, number>;
}

export interface NotApproved {
  action: ActionOut;
  reason: string;
}

export interface BatchApproveResult extends Page<ActionOut> {
  /** Connector writes whose connection has writes disabled: still pending. */
  not_approved: NotApproved[];
}

export interface ActionSecret {
  kind: string;
  value: string;
}

export interface ActionCreate {
  kind: WriteKind;
  app_id: Uuid;
  /** Needed by create_account. */
  person_id?: Uuid | null;
  /** Needed by delete_account. */
  account_id?: Uuid | null;
  email?: string | null;
  role?: string | null;
}

export interface OffboardSkipped {
  account: AccountRef;
  app: AppRef;
  reason: OffboardSkipReason;
}

export interface OffboardResult {
  batch_id: Uuid;
  person: PersonRef;
  actions: ActionOut[];
  skipped: OffboardSkipped[];
}

export interface OnboardApp {
  app_id: Uuid;
  role?: string | null;
}

export interface OnboardRequest {
  /** A repeated app_id counts once. */
  apps: OnboardApp[];
  /** Defaults to the person's primary e-mail. */
  email?: string | null;
}

export interface OnboardSkipped {
  app: AppRef;
  reason: OnboardSkipReason;
}

/** Actions wait for approval as one batch. 400 when the person has left. */
export interface OnboardResult {
  batch_id: Uuid;
  person: PersonRef;
  actions: ActionOut[];
  skipped: OnboardSkipped[];
}

// --- Browser ---------------------------------------------------------------

export interface BrowserTab {
  id: string;
  url: string;
  title: string | null;
  app_id: Uuid | null;
}

export interface BrowserApp {
  app_id: Uuid;
  name: string;
  connector_key: string | null;
  login_url: string | null;
  /** needs_login: the admin has to log in again; null without a connection. */
  connection_status: ConnectionStatus | null;
  last_error: string | null;
}

export interface BrowserState {
  available: boolean;
  live_view_url: string | null;
  tabs: BrowserTab[];
  /** Chromium version, e.g. Chrome/156.0.8078.79. */
  version: string | null;
  /** Why the browser is not available. */
  error: string | null;
  /** Apps with a browser connector (or integration browser). */
  apps: BrowserApp[];
}

export interface BrowserOpenRequest {
  url?: string | null;
  app_id?: Uuid | null;
}

// --- Audit -----------------------------------------------------------------

export interface AuditEventOut {
  id: Uuid;
  at: DateTimeString;
  actor: string;
  event: string;
  entity_type: string;
  entity_id: Uuid | null;
  data: Record<string, unknown> | null;
  /** App the event is about. */
  app_id: Uuid | null;
  /** Person the event is about. */
  person_id: Uuid | null;
}

// --- Currencies and exchange rates (skills/frontend/currency.md) ---------

export interface ExchangeRatesInfo {
  /** Day of the newest stored rates (YYYY-MM-DD). */
  rates_date: string;
  source: string;
  source_url: string | null;
  fetched_at: DateTimeString;
  currencies: number;
}

export interface CurrencyList {
  codes: string[];
  with_rates: string[];
  rates: ExchangeRatesInfo | null;
}
