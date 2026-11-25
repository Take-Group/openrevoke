// App catalog (tag "catalog" in docs/openapi.json): full name, website and logo of known SaaS apps.

export type CatalogMatchedBy = "client_id" | "name";

export interface CatalogAppOut {
  slug: string;
  name: string;
  website: string;
  /** Bundled logo served by the API; null when the app has none. */
  logo_url: string | null;
  /** Normalized names (lowercase letters and digits) the app is found by. */
  keys: string[];
}

export interface CatalogAppList {
  items: CatalogAppOut[];
}

/** What the catalog knows about a found app. `name`: only the name matched, not the Google OAuth client. */
export interface CatalogMatchOut {
  slug: string;
  name: string;
  website: string;
  logo_url: string | null;
  matched_by: CatalogMatchedBy;
}
