/** Shared browser (/api/browser), from docs/openapi.json. */

import type { ConnectionStatus, Uuid } from "@/lib/api/types";

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
