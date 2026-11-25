# Skill: frontend to API communication

## What it does

The panel calls the backend REST API (FastAPI) through React Query 5. The browser
always calls the same origin (`/api/...`), and Next.js forwards the request
to FastAPI. Because of this, the panel needs no CORS and no public API
address.

## Files

- `frontend/next.config.ts`: rewrite `/api/:path*` to
  `${API_PROXY_TARGET}/api/:path*`, by default `http://127.0.0.1:8000`
  (self-hosting: API and frontend in one `app` container). The local dev
  stack sets `API_PROXY_TARGET=http://open-revoke-app:8000` in the `web` service.
- `frontend/src/lib/api/types.ts`: response and request types, copied
  by hand from `docs/openapi.json`. Names as in `components.schemas`.
- `frontend/src/lib/api/client.ts`: `apiFetch`, `apiGet`, `apiSend`,
  `buildQuery`, the `ApiError` class (`status`, `detail`), `errorMessage`,
  `isNotImplemented` (HTTP 501).
- `frontend/src/hooks/use-api-mutation.ts`: `useApiMutation`, the shared
  behaviour of writes (a toast with `detail`, query invalidation).
- `frontend/src/hooks/use-<resource>.ts`: one hook module per resource,
  list in `pages.md`.
- `frontend/src/components/providers.tsx`: `QueryClient` (no retries
  for 4xx and 501) and `Toaster` (sonner).
- `frontend/src/components/common/query-state.tsx`: loading, an error
  with a "Try again" button, a "not available yet" message for 501.

## Flow

1. A component calls a hook, e.g. `usePeople({ q, status })`.
2. The hook calls `apiGet("/api/people", params)`. `buildQuery` skips empty
   values and turns arrays into a repeated parameter
   (`status=a&status=b`, as `GET /api/actions` expects).
3. Next.js rewrites `/api/people` to `API_PROXY_TARGET`.
4. A non-2xx response gives an `ApiError` with the `detail` field from FastAPI.
   A 422 error (a `{loc, msg}` list) turns into one readable text.
5. A write goes through `useApiMutation`: on success it invalidates the given
   resources and always `dashboard` and `audit`; on error it shows a toast.
   `toastErrors: false` turns the toast off when the component shows the error itself
   (e.g. "Approve" with a link to the connection settings).

## Session and client header

`apiFetch` sends `X-Open-Revoke-Client: panel` with every request. Without
it, the API rejects POST, PATCH and DELETE (403, CSRF protection).
The API sets the session cookie, and the browser sends it by itself. A 401 response
refreshes the `["auth"]` query (`providers.tsx`), and `AuthGate` redirects to
`/login`. Exception: mutations with `meta.authFlow` (a wrong password or code during
sign-in). Details: `skills/frontend/auth.md`.

## Query keys

The first element of a key is the resource name: `dashboard`, `people`, `person`,
`apps`, `app`, `accounts`, `connectors`, `sync-runs`, `actions`, `browser`,
`audit`, `auth`, `users`, `invites`. A write invalidates whole resources by this name (the `ResourceKey` type).

## Endpoints with HTTP 501

An endpoint from a later stage responds with 501. `QueryState` then shows
"… is not available yet", and the write toast says the same. The screen is ready
and will work when the backend adds the endpoint. Chrome still logs
"Failed to load resource: 501" in the console; page code cannot silence this.

## Running locally

The local dev stack (`compose.dev.yaml`) runs
the panel as the `web` service (`next dev`, hot reload) at
http://localhost:18410. Lint and typecheck:
`dc exec web bun run lint`, `dc exec web bun run typecheck`. Do not
run `bun run dev` on the host next to the stack (`frontend/AGENTS.md`).

`next build` writes the rewrites into the build. So the `API_PROXY_TARGET` variable
works with `next dev` or at build time, not when the
built `standalone` server starts.

## When the API contract changes

1. The backend refreshes `docs/openapi.json` (`skills/backend/domain-model.md`).
2. Generate a copy of the types for comparison and apply the differences to `types.ts`:
   ```bash
   cd frontend && bunx openapi-typescript ../docs/openapi.json -o /tmp/open-revoke-api.d.ts
   ```
   Do not commit the generated file: it has more than 600 lines (the file
   size limit).
3. `bun run typecheck` shows the places that need fixing.

## How to extend

- New resource: types in `types.ts`, a hook in `src/hooks/use-<resource>.ts`
  (`useQuery` for reads, `useApiMutation` for writes), a new name
  in `ResourceKey`.
- A component does not call `fetch` or `apiFetch` itself. It uses a hook.
