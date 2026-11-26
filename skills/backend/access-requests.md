# Skill: access requests (manager and admin approval)

A person asks for an account in an app (panel "My access", the Slack agent, the API or MCP) with
a justification. The app's `request_policy` decides who approves: the person's manager, an
admin, both, or nobody. Every decision is a row in `access_request_decision` and an audit event.
The account itself comes from a `create_account` action (or a manual task), created after the
manager's step (`skills/backend/actions.md`).

## Files

| File | What |
|---|---|
| `backend/app/services/access/requests.py` | `request_access(person, app, NewRequest)`: checks (leaver 400, policy `off`, justification 400, account exists, open request 409), stores the request, calls `flow.route` |
| `backend/app/services/access/flow.py` | `route` (first step by policy), `decide` (one decision from the panel, the API or Slack), `Decider` (actor, person, may act as admin) |
| `backend/app/services/access/request_sync.py` | `on_action_changed`, called by `actions.advance`: the request follows its action (admin step through `/actions`, done, failed, cancelled, retry) |
| `backend/app/services/access/decisions.py` | `record_decision`, `record_event`, `close`, `ensure_not_own`, `last_rejection`: shared by the flow and the hook, imports no action service |
| `backend/app/services/access/queries.py` | `RequestFilter`, `list_requests`, `detail`, `export_csv` (formula-safe cells), `waiting_for` |
| `backend/app/services/access/my_access.py`, `my_approvals.py` | `/api/me/access`, `/api/me/access-requests`, `/api/me/team`; `/api/me/approvals` (a manager's view and decisions) |
| `backend/app/services/access/managers.py`, `slack_reach.py` | the manager and their panel user; whether a person can be reached on Slack (bot connected, e-mail known) |
| `backend/app/services/access/profiles.py` | `auto_approving_profile`: a profile with `auto_approve_requests` skips the manager step |
| `backend/app/services/auth/actor.py` | `current_actor`, `current_user_id`, `current_via`, `ActorRef`, `actor_ref()`: who decides, set by `api/auth_deps.py` (panel cookie or API token) and by the Slack click |
| `backend/app/api/access_requests.py`, `api/me.py` | admin and user endpoints (below) |
| `backend/app/slack_agent/approvals.py`, `notifier.py` | Slack messages with buttons by step; the result to the person for every channel |
| `frontend/src/components/requests/`, `components/me/` | `/requests`, `/requests/[id]`, `/me`, `/me/request`, `/me/approvals`, `/me/approvals/[id]` |

## Statuses

`pending_manager` → (manager yes) → action created → `approved` (`manager`) or `pending_admin`
(`manager_then_admin`) → (admin yes) → `approved` → `done` / `failed` (from the action).
`rejected` (a no, with a comment), `cancelled` (the action was cancelled after approval).
Open statuses (`OPEN_REQUEST_STATUSES`): `pending_manager`, `pending_admin`, `approved`.

## Flow (`flow.route`)

1. `automatic`: decision `step=admin`, `via=automatic`, by "Automatic (app policy)"; the action is
   approved at once (writes off: it waits for an admin, the request is `pending_admin`).
   A `role` the requester typed that no access profile of theirs gives for the app (connectors map
   `admin` to the app's admin) is never approved automatically: audit `access_request.escalated`
   with `reason=role`, the action waits for an admin. The same check gates the profile shortcut in 3.
2. `admin`: the action waits (`pending_admin`).
3. `manager`, `manager_then_admin`:
   - an access profile of the person with the app and `auto_approve_requests`, or a manager
     asking for their report (`on_behalf`): the manager step is met, `via=automatic`, comment
     "Access profile <name>" or "Requested by the manager";
   - otherwise the manager (`person.manager_id`) decides when they have an active panel account
     (e-mail or alias) or a Slack identity; else `fallback_reason` (`no_manager`, `manager_left`,
     `manager_no_access`, `manager_is_requester` when the person is their own manager), audit
     `access_request.escalated`, and the action waits for an admin.
4. After the manager's yes: `manager` approves the action with the manager as `approved_by`
   (a manual task then waits for the admin to do it by hand; writes off leave it
   `pending_admin`); `manager_then_admin` leaves it for an admin.

## Who decides (`flow.decide`)

- Nobody decides their own request (403, also in `/actions` through `request_sync`).
- The manager step: the manager it waits for (`approver_person_id`), or an admin through
  `/api/access-requests/{id}/approve|reject` ("Decide for the manager", `override=true`, audit
  `access_request.overridden`). `/api/me/approvals/...` never acts as an admin.
- The admin step: an admin (`/requests/[id]`, `/actions` approve or cancel, Slack button).
- A rejection needs a comment (400), except from Slack ("Rejected in Slack.").
- A request that waits for nobody: 409. A manager on an `pending_admin` request: 409.
- `approve` of a connector write with writes off: 400 before anything is recorded.

### The manager changes while a request waits

`flow.refresh_approver` re-checks a `pending_manager` request against the person's current manager:
a new manager takes it over (Slack message again), a manager who left or can no longer decide sends
it to an admin with `fallback_reason`. `decide` runs it first, so a former manager gets 403.
`flow.reroute_pending` runs it for every waiting request after `people.update_person` (manager,
status, e-mails), `offboarding`, the people CSV import and a people sync that changed managers.
Audit event `access_request.rerouted`. The CSV export escapes every cell (`queries._safe`).

## API

| Route | Who | What |
|---|---|---|
| `POST /api/me/access-requests` | user | `app_id`, `justification`, `role?`, `person_id?` (own report) |
| `GET /api/me/access` | user | accounts, requests (status, `waiting_for`, `approver`, `rejection_comment`), requestable apps with `policy` and role suggestions |
| `GET /api/me/team` | user | reports, their apps and what can be asked for them |
| `GET /api/me/approvals?status=` | user | requests waiting (or that waited) for me; `pending`, `has_reports` for the sidebar |
| `GET /api/me/approvals/{id}`, `POST .../approve`, `.../reject` | user | detail and decision; 403 unless my report |
| `GET /api/access-requests` | admin | filters `status` (repeat), `app_id`, `person_id`, `from`, `to`, `waiting_for` |
| `GET /api/access-requests/{id}`, `POST .../approve`, `.../reject` | admin | detail with decisions and action; admin step or override |
| `GET /api/access-requests/export` | admin | CSV with the same filters, one row per request, decisions in one cell |

## Audit events

`access_request.created`, `.manager_approved`, `.manager_rejected`, `.escalated`,
`.admin_approved`, `.admin_rejected`, `.overridden`, `.cancelled`, `.closed`, `.reopened`
(a retry of a failed action); `action.approved` carries `approved_by`.

## Slack

Requests waiting for the manager go to the manager's Slack (`users.lookupByEmail` on their
e-mails); requests waiting for an admin go to every admin on Slack except the requester. Moving
to `pending_admin` clears `approvers_notified_at`, so the admins get their own message. Buttons
carry the request id. The result goes to the person for every channel (a Slack request in its
chat, others in a DM) for requests closed in the last day.

## Check by hand

No tests. Set `person.manager_id` in SQL (or on `/people/[id]`), sign in as
`member@example.com`, ask on `/me/request`; as `manager@example.com` decide on `/me/approvals`;
as admin see `/requests`, `/requests/[id]` and Export CSV. Slack paths: call
`approvals.notify_pending`, `approvals.handle_click`, `notifier.notify_finished` with
`web_api.call` replaced by a fake in a one-off script inside the `api` container.
