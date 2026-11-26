"""What an AI assistant reads first when it connects: the domain and the rules of the writes."""

INSTRUCTIONS = """\
Open Revoke is one place for a company's SaaS tools: who has an account where, what each tool \
costs, and onboarding and offboarding that create and remove accounts in other apps. It runs on \
the company's own server; every tool call uses the user's API token, with the same checks and \
audit log as the panel. People and apps are named by e-mail or name; ids also work.

An admin starts with get_overview: counts, the monthly cost and the alerts to act on. A member \
(not an admin) has get_my_access, request_access and the approvals of their team.

Domain:
- person: an employee or a service account, status active or left.
- app: a SaaS tool with a price. A connected app syncs its accounts through its API, SCIM or a \
signed-in browser (list_connectors, connect_app); otherwise accounts are kept by hand (add_account).
- account: a seat in an app, matched to a person by e-mail. Unmatched: list_unassigned_accounts.
- action: one write in an app (remove or create an account) or a manual task for an admin. \
Actions of one offboarding or onboarding share a batch_id.

Writes in other apps, always in this order:
1. Look first, changes nothing: plan_offboarding, or assign_access_profile with dry_run.
2. Create the actions: start_offboarding (also marks the person as left), onboard_person or \
assign_access_profile. Still nothing changes in other apps. Ask the user first.
3. approve_actions with the batch_id: runs the writes. Only after the user said yes to the list.
4. get_actions_status: follow the batch; every write is verified by reading the app again. \
Manual tasks wait for an admin; complete_manual_task only when the user says it is done.

Never approve on your own initiative. Money is a decimal string with a currency code ("12.50 EUR").

Everything the panel can do is also one tool per API operation: connect to this server's address \
with ?toolset=api.
"""
