# Skill: App catalog (names, websites and logos of known SaaS apps)

## What it does

A Google Workspace scan learns two things about a third-party app: the name
from its OAuth consent screen ("fathom.video") and its OAuth client id. Google
gives no logo and no website. The catalog adds them for known apps: full name
("Fathom"), website and a bundled logo. The panel shows them in discovery
(list, detail, a person's apps) and, by name, in every `AppAvatar`. "Track"
names the new app with the catalog name.

The app's vendor sets the consent-screen name and the client id, so both are
the same in every Google Workspace: one list in the repo works for every
company. The list must hold public SaaS apps only, never one company's own
internal OAuth apps.

## Files

| File | What it does |
|---|---|
| `backend/app/catalog/apps.json` | the list: `slug`, `name`, `website`, optional `aliases`, `match_name`, `logo`, `fetch_logo`, `login_url`, `google_client_ids` |
| `backend/app/catalog/logos/<slug>.png` | 128x128 PNG logos, committed; made by the script below |
| `backend/app/catalog/lookup.py` | `app_catalog()` (loaded once per process), `AppCatalog.match(name, client_ids)`, `by_name`, `logo_path`, `normalize` |
| `backend/app/schemas/catalog.py` | `CatalogAppOut`, `CatalogAppList`, `CatalogMatchOut` (with `matched_by`) |
| `backend/app/api/catalog.py` | public GET `/api/catalog/apps`, GET `/api/catalog/logos/{slug}.png` |
| `backend/app/services/discovery.py` | `catalog_match` fills `catalog` of `DiscoveredAppOut` and `PersonDiscoveredApp` |
| `backend/app/services/discovery_review.py` | Track uses the catalog name |
| `backend/scripts/fetch_catalog_logos.py` | downloads logos from the apps' websites (run by hand) |
| `backend/scripts/probe_google_sign_in.py` | reads client ids from the apps' public sign-in pages (run by hand) |
| `frontend/src/hooks/use-catalog.ts` | `useAppCatalog()`: lookup by catalog slug or app name |
| `frontend/src/components/common/avatars.tsx` | `AppAvatar`: simple-icons mark, then catalog logo, then initials |

## Matching

1. OAuth client id on the list: this is the app (`matched_by: client_id`).
   When two entries share the ids (Grok and xAI), the entry with the app's
   name wins.
2. Otherwise the normalized name (lowercase letters and digits) against the
   entry's `name`, `aliases` and website host (`matched_by: name`).

Any OAuth app can call itself "Slack", so a name match is a hint, not proof;
the detail page says so next to the website. Set `"match_name": false` for a
common word or a name two products share (Apollo, Tally, Spark, X, Fathom):
then only client ids and `aliases` match.

The panel looks up apps by name too (`keys` from `/api/catalog/apps`,
normalized like `brand-icons.ts` `normalizeName`), so tracked apps and
people's accounts get the logo without a change in their API schemas.

## Add or fix an app

1. Add the entry to `apps.json` (keep it sorted by `slug`). A client id may
   appear in one entry only. Two sources of client ids:
   - a real scan: `dc exec postgres psql -U postgres -d open_revoke -c "select name, client_ids from discovered_app"`;
   - the app's public sign-in page. Its "Sign in with Google" button sends the
     client id to Google, and Google's page names the app ("to continue to
     X"). From `open-revoke/backend` on the host:
     `uv run --no-project --with playwright python scripts/probe_google_sign_in.py --out /tmp/probe.json <slug>`
     (`--more` tries less common sign-in addresses; set `login_url` when both
     miss). Read the report: a name that is not the brand (`workos.com`,
     another company) is an auth provider's client, drop it. An id on two
     apps' pages is dropped by the script (Loom and Trello sign in with
     Atlassian's). Then `--apply /tmp/probe.json`. Checked on 24.11.2026:
     the ids it read for Slack, Miro, Figma and Clay equal the ones from a
     real Workspace scan.

   Reuse another app's logo with `"logo": "<slug>"` (Notion Calendar uses
   `notion`).
2. Download its logo, from `open-revoke/backend` on the host:
   `uv run --no-project --with httpx --with pillow --with beautifulsoup4 python scripts/fetch_catalog_logos.py <slug>`
   (`--force` downloads again). Check the printed page title: a redirect to
   another company means a wrong or sold domain.
3. Look at the PNG. If the site gives a bad icon, replace the file by hand
   (128x128 PNG, transparent background or a full-bleed square), or set
   `"fetch_logo": false` and delete it: initials beat another brand's logo.
   A white mark gets a dark square, or it would vanish on the white tile.
4. The API reads the list at start: uvicorn `--reload` restarts on `.py`
   changes only, so run `dc restart api` after editing `apps.json` or logos.

Leave out apps you cannot identify for sure (a generic name, no website).
A wrong logo next to an OAuth grant misleads an admin more than initials do.

Logos are trademarks of their owners, used only to name the product; they
are not covered by the repo's MIT license.
