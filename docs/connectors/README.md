# Connectors

A connector reads the accounts of one app and, when you allow writes, creates and removes them.
Open Revoke talks to an app in one of three ways:

1. **Official API** (for example the Google Admin SDK or the GitHub REST API).
2. **SCIM 2.0**, for any app that exposes a SCIM endpoint. One generic connector covers all of them.
3. **A real browser session.** Chromium runs in Docker. An admin logs in to the app's admin panel
   through a live view in Open Revoke. The connector then sends the same HTTP requests the admin
   panel sends, from inside that logged-in tab.

Apps without a connector use the integration `manual`: you enter accounts by hand, and onboarding
or offboarding creates a checklist task instead of a write.

## List

| Connector | Method | Reads | Creates | Removes | Verified on a real account |
|---|---|---|---|---|---|
| [Google Workspace](google_workspace.md) | Admin SDK Directory API, "Connect with Google" (OAuth) or a service account with domain-wide delegation | users, also as a source of people; sign-ins to third-party apps (app discovery) | user with a temporary password shown once | suspends the user | Reading and app discovery: yes. Writes: no |
| [GitHub](github.md) | REST API, organization token | members and pending invitations | invitation to the organization | removes from the organization or cancels the invitation | No. Written from the public API docs |
| [SCIM 2.0](scim.md) | SCIM, bearer token | `GET /Users` | `POST /Users` | `active: false` or `DELETE /Users/{id}` | No. Written from RFC 7643 and RFC 7644 |
| [Slack](slack.md) | browser session: web client API for reads, a click recipe in the admin page for writes | members, plan and price from billing | invitation | deactivation | Yes, on a Pro workspace |
| [Claude (Team)](claude-team.md) | browser session, private claude.ai endpoints | members and pending invites | invitation | removes the member or revokes the invite | No. Endpoints are a best guess, not recorded yet |
| [ChatGPT (Team)](chatgpt.md) | browser session, private chatgpt.com endpoints | members and pending invites | invitation | removes the member or revokes the invite | No. Endpoints are a best guess, not recorded yet |

Most connectors are not verified on real accounts yet. Keep "Allow writes" off for a connection
until a sync has shown you the account list you expect, and test writes on a test account first.
Google Workspace removal suspends the user and never deletes: deletion removes mail and files for
good.

## Safety rules

- Every write (an invitation, a removal) waits for a person to approve it, runs in the background
  and is then checked by reading the app's account list again. A write that the read does not
  confirm ends as failed, even if the app answered 200.
- A connector returns the full account list or fails. It never returns part of a list.
- If one sync would mark more than 30% of an app's accounts as removed, it stops and changes
  nothing. When the removals are real, run the sync again with force.
- An account you assigned to a person by hand keeps that owner across syncs.

## Browser login

1. Add the app in **Apps**, choose the integration `browser` and save a browser connector (Slack,
   Claude or ChatGPT) in the app's connection settings.
2. Open **Browser** in the panel. It embeds the live view of the shared Chromium. Click
   **Log in** next to the app: the app's login page opens in that Chromium.
3. Log in by hand in the live view, including 2FA. Open Revoke never sees your password.
4. Click **Sync now** on the app. The connector reads the member list from inside the logged-in tab.

The session lives in the `browser-profile` Docker volume and survives container restarts. Anyone
with this volume has those sessions: do not copy it (`docker compose down -v` deletes it). When the
app logs you out, the next sync ends with the status `needs_login` (not with removed accounts) and
the dashboard asks you to log in again. The live view has no port of its own: the API passes it to
the panel after it checks the admin's session.

## Add a connector

A connector is one Python package per app in `backend/app/connectors/<key>/`. It reads accounts and
optionally creates and removes them; it never writes to the database. The guide is
[skills/backend/new-connector.md](../../skills/backend/new-connector.md).

For browser connectors, record what the admin panel does while you click through it in the live
view:

```bash
docker compose exec app python -m app.devtools.capture --host app.slack.com --out captures/slack.jsonl
```

The tool saves every fetch/XHR request to that host as JSON lines, with tokens and auth headers
masked. The file still contains real names and e-mails: `captures/` is in `.gitignore`, keep it out
of git and delete it when the connector is done. Details:
[skills/backend/browser.md](../../skills/backend/browser.md).
