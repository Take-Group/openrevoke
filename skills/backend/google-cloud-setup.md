# Skill: Automatic Google Cloud setup (Connect with Google, "Automatic")

## What it does

The Discovery page offers three ways to connect Google Workspace: **Automatic**
(this skill), **Guided (links)** (the admin creates the OAuth client by hand,
`docs/connectors/google_workspace.md`) and a **service account key**.

Automatic: the admin signs in to Google in the shared browser (live view on
the page) and clicks "Set up automatically". The worker then drives the Google
Cloud console over CDP:

1. reads the signed-in account (`Account: Name (email)` button),
2. creates a project (name "Open Revoke"; a new run reuses the project ID it
   stored),
3. enables the Admin SDK API,
4. runs the Google Auth Platform wizard: app name, support e-mail, audience
   **Internal**, contact e-mail, ticks "I agree to the Google API Services:
   User Data Policy" (the panel says so before the start),
5. creates a Web application OAuth client with the redirect URI and reads the
   client ID and secret from the "OAuth client created" dialog (Google shows
   the secret only there),
6. opens Google's consent screen in the same tab; the admin chooses the
   account and clicks Allow in the live view,
7. catches the redirect to the callback URL and runs the same code as the
   guided flow (`google_oauth.finish`: refresh token, scope check, app and
   connection as people source, sync, scan).

Checked end to end on a real Workspace on 23.11.2026: people imported,
scan found the apps.

## Files

| File | What |
|---|---|
| `backend/app/services/google_cloud_setup/console.py` | console steps (Playwright `Page`), every URL with `hl=en`, English labels |
| `backend/app/services/google_cloud_setup/runner.py` | order of the steps, progress, errors to the state |
| `backend/app/services/google_cloud_setup/state.py` | progress in Redis (`open-revoke:google-cloud-setup`), stale after 20 min without a write |
| `backend/app/services/google_cloud_setup/service.py` | start (409 when running or already connected), read |
| `backend/app/temporal/google_setup_*.py` | `GoogleCloudSetupWorkflow`, one activity, no retries (a retry would create clients again), heartbeat |
| `backend/app/api/google_cloud_setup.py` | `GET`/`POST /api/discovery/google-cloud-setup` |
| `frontend/src/components/discovery/google-auto-setup.tsx` | steps, hint, start button, live view |

## Pitfalls

- **No `networkidle`.** The console keeps connections open; wait for the
  element you need.
- **Redirects and `page.route`.** Google returns to the redirect URI with an
  HTTP redirect; `page.route` does not see redirects. `await_redirect`
  watches `context.on("request")` instead. The redirect URI points at the
  panel on the admin's computer, which the container cannot open: the page
  shows a connection error for a moment, then a short note.
- **Labels.** Selectors are role + English label from the aria snapshot. When
  Google changes a page, the run fails with the step name; check the page
  with the MCP server `open-revoke-browser` (`app/.mcp.json`) or
  `page.locator("body").aria_snapshot()` and fix `console.py`.
- **Google session.** Restarting the `browser` container signed the account
  out ("Signed out" in the account chooser) on 23.11.2026, although the
  cookies stayed; cause not checked. Sign in again in the live view.
- **Worker code.** After editing these files, check that the worker runs the
  new code (`dc restart worker` when unsure): a run once failed with code
  from before an edit.
- Each run creates a new OAuth client in the project; unused ones stay in
  Google Auth Platform, Clients.
