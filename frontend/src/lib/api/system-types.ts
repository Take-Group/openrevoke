// GET /api/system/version: this installation's version and the update notice (docs/openapi.json).

export interface SystemVersion {
  /** Version of this installation; `dev` in the local stack. */
  version: string;
  /** The hourly check for a newer release is on (OPEN_REVOKE_UPDATE_CHECK). */
  update_check: boolean;
  latest_version: string | null;
  /** Release notes of the newest release. */
  latest_url: string | null;
  latest_published_at: string | null;
  checked_at: string | null;
  update_available: boolean;
  /** The newer release has a Security section in its notes. */
  security_update: boolean;
}
