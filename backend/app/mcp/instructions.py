"""What an AI assistant reads first when it connects: the domain and the rules of the writes."""

INSTRUCTIONS = """\
Open Revoke is one place for a company's SaaS tools: who has an account where, what each tool \
costs, and offboarding that removes a leaver's accounts. Every tool is one call of the panel's API \
with the user's API token: the same checks, the same audit log.

Domain:
- person: an employee or a service account (kind). status active or left. People come from Google \
Workspace, CSV import or are added by hand.
- app: a SaaS tool with a price (per seat, flat or free). An app may have a connection (connector \
with settings and secrets) that syncs its accounts; without one, accounts are kept by hand.
- account: a seat in an app, matched to a person by e-mail.
- action: a write in an app (create_account, delete_account) or a manual_task. Lifecycle: \
pending_approval, approved, running, verifying, done, failed or cancelled.
- discovered app: a third-party app people signed in to with the company Google account.
- panel user: someone who signs in to Open Revoke (admin or user). Not a person.

How to work:
- Ids are UUIDs. Find them first: list_people and list_apps take q (search), then get_person or get_app.
- Connecting an app: list_connectors gives each connector's settings schema, then put_connection, \
check_connection, sync_connection. Secrets in put_connection are encrypted and never returned.
- offboard_person and onboard_person only create actions waiting for approval. approve_action and \
approve_action_batch run them: accounts are really removed or created in other apps. Show the user \
what will happen and get a clear yes before any approve, retry or delete.
- A sync, a scan or an action runs in the background: poll list_sync_runs, get_discovery or list_actions.
- Money is a decimal string ("12.50") with a currency code.
- Connect with Google and the Slack app install need the admin's browser: give the user the link a \
tool returns, or point them to the panel.
"""
