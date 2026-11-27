# open-revoke/docs/

Product docs, public with the repo: no plans and no business data (market, competitors, prices, the company's own accounts) here.

- `browser-recipes.md`: click recipes for writes in apps without an API: decision (API, SCIM, browser, manual), JSON format, locators, safety, repair by AI.
- `self-hosting.md`: install under your own domain: `PUBLIC_URL`, HTTPS with Caddy, own proxy or VPN, Google redirect rules.
- `kubernetes.md`: the Helm chart (`deploy/helm/openrevoke`): install, values, external database, backup, update, uninstall, move from Compose, limits.
- `security/`, no map: `overview.md` (answers for a customer's security review), `threat-model.md` (assets, trust boundaries, STRIDE threats with controls and accepted risks; update it with any change to auth, secrets, the browser, writes or releases).
- `openapi.json`: API contract, source of the frontend types (`frontend/src/lib/api/types.ts`).
- `connectors/`: own AGENTS.md. How to connect each app, endpoints, limits.
- `assets/`, no map: images of the repo README: `logo-light.svg`, `logo-dark.svg` (full logo, `<picture>` picks by GitHub theme), `panel.png` (dashboard on seed data only, never a real organization: take it from a stack without `SEED_GOOGLE_*`).
