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

/** A catalog app as "Add app" offers it (GET /api/catalog/search, admins only). */
export interface CatalogSearchItem {
  slug: string;
  name: string;
  website: string;
  logo_url: string | null;
  /** Connector that reads this app's accounts, when there is one. */
  connector_key: string | null;
  /** Id of the app already in Open Revoke (same catalog_key or name). */
  already_added: string | null;
  /** People who signed in with Google, when discovery found the app and nobody tracks it yet. */
  discovered_users: number | null;
}

export interface CatalogSearchList {
  items: CatalogSearchItem[];
}
