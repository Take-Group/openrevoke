// Fast inventory: catalog fields of an app, apps in bulk, accounts from a CSV or pasted e-mails.

import type { AppListItem, AppRef, ImportRowAction, Page, PersonRef, Uuid, FieldChange } from "@/lib/api/types";

/** Suggested categories; the field takes any text. */
export const APP_CATEGORIES = [
  "communication",
  "development",
  "design",
  "ai",
  "sales",
  "finance",
  "hr",
  "security",
  "infrastructure",
  "productivity",
  "other",
] as const;

export interface AppCatalogFields {
  /** Slug in the app catalog, when the app was picked from it. */
  catalog_key: string | null;
  website: string | null;
  category: string | null;
  /** Uploaded logo (`/api/apps/<id>/logo`), else the catalog's; null without one. */
  logo_url: string | null;
}

export interface AppCatalogInput {
  catalog_key?: string | null;
  website?: string | null;
  category?: string | null;
}

export interface AppPage extends Page<AppListItem> {
  /** Every category in use, for the filter. */
  categories: string[];
}

export interface AppBulkItem {
  catalog_key?: string | null;
  name?: string | null;
}

export interface AppBulkSkipped {
  name: string;
  catalog_key: string | null;
  reason: string;
  app_id: Uuid | null;
}

export interface AppBulkResult {
  created: AppRef[];
  skipped: AppBulkSkipped[];
}

export interface AccountImportRow {
  line: number;
  app: string;
  app_id: Uuid | null;
  email: string | null;
  username: string | null;
  display_name: string | null;
  action: ImportRowAction;
  account_id: Uuid | null;
  person: PersonRef | null;
  changes: FieldChange[];
  errors: string[];
}

export interface AccountImportNewApp {
  name: string;
  catalog_key: string | null;
  app_id: Uuid | null;
}

export interface AccountImportResult {
  dry_run: boolean;
  created: number;
  updated: number;
  unchanged: number;
  failed: number;
  rows: AccountImportRow[];
  new_apps: AccountImportNewApp[];
}
