# GitHub connector

Key: `github`. Method: GitHub REST API with a token. Code:
`backend/app/connectors/github/`.

The connector reads the members of one organization and its pending
invitations. It creates an account through an e-mail invitation, and it
removes a member from the organization or cancels an invitation.

## How to connect

An organization owner issues the token. Two options:

1. **Fine-grained personal access token** (recommended): Settings, Developer
   settings, Fine-grained tokens. Resource owner: the organization. Organization
   permissions, **Members**: `Read-only` (read) or `Read and write`
   (invitations and removal). The organization may require the owner to
   approve the token.
2. **Classic personal access token**: scope `read:org` to read,
   `admin:org` to write.

In Open Revoke: an app with the `api` integration, connection `github`:

- `org`: the organization login, as in `github.com/<org>`,
- `api_url`: leave `https://api.github.com`; for GitHub Enterprise Server
  enter `https://<host>/api/v3`,
- `token`: the secret.

Store the token in a password manager. It has an expiry date: after it
expires, sync ends with `needs_login`, and the accounts stay unchanged.

## Endpoints

Headers: `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`,
`X-GitHub-Api-Version: 2022-11-28`.

| Operation | Call |
|---|---|
| `check` | `GET /orgs/{org}`, then `GET /orgs/{org}/members?per_page=1` |
| `list_accounts` | `GET /orgs/{org}/members?role=all&per_page=100`, `GET /orgs/{org}/members?role=admin&per_page=100`, `GET /orgs/{org}/invitations?per_page=100`; next pages from the `Link` header (`rel="next"`) |
| `create_account` | `POST /orgs/{org}/invitations` with `{"email": …, "role": "direct_member"}` (or `admin`) |
| `delete_account` | member: `DELETE /orgs/{org}/members/{login}`; invitation: `DELETE /orgs/{org}/invitations/{id}` |

## Mapping

- Member: `external_id` = the numeric `id` of the GitHub user (it does not
  change when the login changes), `username` = `login`, role `admin` when
  the user is on the `role=admin` list, otherwise `member`. Status `active`.
- Invitation: `external_id` = `invitation:{id}`, `email` from the invitation
  (when invited by e-mail), `username` = login (when invited by login), role
  `member` or `admin`, status `invited`.
- An accepted invitation disappears from the invitation list and appears as
  a member with a different `external_id`. Sync marks the invitation as
  `removed` and the member as a new account.

## Limits

- The members API does not return the e-mail. A person assigns GitHub
  accounts (`PATCH /api/accounts/{id}`), and the assignment survives later syncs.
- Outside collaborators (access to repositories without membership) are not
  read. On paid plans they take seats in private repositories
  (not verified).
- Concealed members are visible when the token belongs to a member of the
  organization.
- Failed invitations (`/orgs/{org}/failed_invitations`) are not read.
- Rate limits: 5000 requests per hour per token (not verified for 11.2026).
  An organization of 100 people needs a few requests per sync.
- 403 (missing permission or rate limit) is a sync error, not `needs_login`.
- Paths and parameters are checked against knowledge of the REST API
  (version 2022-11-28), not on a real organization (status 22.11.2026).
