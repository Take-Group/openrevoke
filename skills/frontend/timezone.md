# Skill: Frontend timezone

## What it does

Formats every date in the organization's time zone (chosen in the
first-run setup, suggested from the computer's zone, changed in
`/settings`), regardless of the viewer's device. Before the auth state
loads, the build-time default `Europe/Warsaw` applies.

## Files involved

- `compose.yaml` — sets `TZ` on the `app` service (self-hosting);
  `compose.dev.yaml` sets `TZ` and `NEXT_PUBLIC_TIME_ZONE` on the `web`
  service (`next dev`, local dev stack)
- `Dockerfile` — the `frontend-build` stage sets `NEXT_PUBLIC_TIME_ZONE` so it
  is inlined into the client bundle; the `app` target installs `tzdata` and
  sets both variables for the production runtime
- `frontend/src/lib/date-time.ts` — shared `formatDateTime` formatter,
  `setAppTimeZone` (called by `components/auth/auth-gate.tsx` with
  `organization.timezone`)

## Flow

1. The Next.js server runs with `TZ=Europe/Warsaw`.
2. `NEXT_PUBLIC_TIME_ZONE` makes the same setting available in browser code.
3. `AuthGate` sets the organization's zone before the panel renders and
   remounts the panel when it changes.
4. `formatDateTime` always passes the explicit timezone to
   `Intl.DateTimeFormat` and uses the `pl-PL` locale.

## How to extend

- Use `formatDateTime` instead of calling `toLocaleString()` directly.
- In the panel use `formatWhen` from `frontend/src/lib/format.ts`: numeric
  `22.11.2026, 18:24` (no Polish month names in the English UI) and `—`
  for null.
- For a live clock based on the current moment, render it after client mount
  to avoid a Next.js hydration mismatch.
- Keep API timestamps unambiguous, preferably ISO 8601 with an explicit
  offset or `Z`.
