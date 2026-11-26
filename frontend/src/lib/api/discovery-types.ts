// App discovery types (tag "discovery" in docs/openapi.json). Separate from types.ts, which is near
// the 600-line limit. Names match `components.schemas` in the contract.

import type { CatalogMatchOut } from "@/lib/api/catalog-types";
import type { ConnectionStatus, DateTimeString, PersonStatus, Uuid } from "@/lib/api/types";

export type ScanRunStatus = "running" | "ok" | "failed";
export type DiscoveredAppStatus = "new" | "tracked" | "ignored";
export type DirectoryStatus = "active" | "suspended" | "deleted" | "external";
export type GrantRisk = "left" | "suspended" | "deleted";

export interface ScanRunOut {
  id: Uuid;
  connection_id: Uuid;
  started_at: DateTimeString;
  finished_at: DateTimeString | null;
  status: ScanRunStatus;
  events_from: DateTimeString | null;
  events_until: DateTimeString | null;
  users_scanned: number;
  apps_found: number;
  apps_new: number;
  grants_found: number;
  token_inventory: boolean | null;
  notes: string[] | null;
  error: string | null;
}

export interface DiscoveryConnector {
  key: string;
  display_name: string;
  required_scopes: string[];
  optional_scopes: string[];
}

export interface DiscoverySource {
  connection_id: Uuid;
  app_id: Uuid;
  app_name: string;
  connector_key: string;
  connection_status: ConnectionStatus;
  last_synced_at: DateTimeString | null;
}

export interface DiscoveryCounts {
  apps: number;
  apps_new: number;
  apps_tracked: number;
  apps_ignored: number;
  people: number;
  grants_at_risk: number;
  apps_at_risk: number;
}

export interface DiscoveryOverview {
  source: DiscoverySource | null;
  connectors: DiscoveryConnector[];
  last_scan: ScanRunOut | null;
  last_successful_scan: ScanRunOut | null;
  scan_running: boolean;
  counts: DiscoveryCounts;
  /** Authorized redirect URI for the company's Google OAuth client (Connect with Google). */
  google_oauth_redirect_uri: string;
}

export interface DiscoverySourceCreate {
  admin_email: string;
  service_account_json: string;
  customer?: string;
  domain?: string | null;
}

export interface GoogleOAuthStart {
  client_id: string;
  client_secret: string;
  customer?: string;
  domain?: string | null;
}

export interface GoogleOAuthStartOut {
  authorization_url: string;
}

export interface LinkedApp {
  id: Uuid;
  name: string;
}

export interface DiscoveredAppOut {
  id: Uuid;
  /** Name from the app's Google consent screen. */
  name: string;
  /** Full name, website and logo from the app catalog. */
  catalog: CatalogMatchOut | null;
  status: DiscoveredAppStatus;
  app: LinkedApp | null;
  client_ids: string[];
  scopes: string[];
  first_seen_at: DateTimeString | null;
  last_seen_at: DateTimeString | null;
  users: number;
  users_at_risk: number;
  active_tokens: number | null;
}

export interface GrantPerson {
  id: Uuid;
  name: string;
  status: PersonStatus;
}

export interface DiscoveredGrantOut {
  id: Uuid;
  email: string;
  person: GrantPerson | null;
  directory_status: DirectoryStatus;
  deleted_at: DateTimeString | null;
  first_seen_at: DateTimeString | null;
  last_seen_at: DateTimeString | null;
  token_active: boolean | null;
  scopes: string[];
  risk: GrantRisk | null;
}

export interface DiscoveredAppDetail extends DiscoveredAppOut {
  grants: DiscoveredGrantOut[];
  /** Only in the answer to track with `create_accounts`: accounts it added. */
  accounts_created?: number | null;
}

export interface DiscoveredAppUpdate {
  status?: DiscoveredAppStatus;
  app_id?: Uuid | null;
}

export interface PersonDiscoveredApp {
  discovered_app_id: Uuid;
  name: string;
  catalog: CatalogMatchOut | null;
  status: DiscoveredAppStatus;
  app: LinkedApp | null;
  email: string;
  directory_status: DirectoryStatus;
  first_seen_at: DateTimeString | null;
  last_seen_at: DateTimeString | null;
  token_active: boolean | null;
  has_account: boolean;
}

export type GoogleCloudSetupStatus = "running" | "needs_sign_in" | "waiting_for_consent" | "connected" | "failed";
export type GoogleCloudSetupStepKey =
  | "sign_in"
  | "project"
  | "api"
  | "consent_screen"
  | "client"
  | "consent"
  | "import";

export interface GoogleCloudSetupStep {
  key: GoogleCloudSetupStepKey;
  label: string;
  state: "pending" | "active" | "done" | "failed";
}

/** Automatic Google Cloud setup in the shared browser; `status` is null before the first run. */
export interface GoogleCloudSetupOut {
  status: GoogleCloudSetupStatus | null;
  step: GoogleCloudSetupStepKey | null;
  steps: GoogleCloudSetupStep[];
  project_id: string | null;
  admin_email: string | null;
  error: string | null;
  started_at: DateTimeString | null;
  finished_at: DateTimeString | null;
}

export interface GoogleCloudSetupStart {
  project_name?: string;
}
