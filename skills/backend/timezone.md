# Skill: Backend timezone

## What it does

Configures every backend container to use the `Europe/Warsaw` IANA timezone,
including automatic daylight-saving time changes.

## Files involved

- `compose.yaml` (self-hosting) and `compose.dev.yaml`
  entry (local dev stack) — pass `TZ` to every service and configure
  PostgreSQL session and log timezones
- `Dockerfile` — `app` (installs `tzdata` for API, worker and table
  creation), `backend-dev` (the same for the local dev stack), `postgres`
  and `redis` (both add `tzdata`)
- `backend/app/config.py` — exposes the application timezone as
  `settings.timezone`
- `backend/.env.example` — documents the default `TZ`

## Flow

1. Docker Compose passes `TZ=Europe/Warsaw` to every process.
2. Images owned by the project install `tzdata`, so DST rules are available.
3. PostgreSQL starts with `timezone` and `log_timezone` set to
   `Europe/Warsaw`.
4. Application code reads the same value through `settings.timezone`.

Temporal and database timestamps still represent unambiguous instants.
Business rules and presentation convert those instants to `Europe/Warsaw`.

## How to extend

- Add `TZ: Europe/Warsaw` to every new service in `compose.yaml` and in
  `compose.dev.yaml`.
- Install `tzdata` in every new minimal or Alpine-based target added to the
  root `Dockerfile`.
- Use timezone-aware datetimes. Do not persist ambiguous naive local
  datetimes.
