---
name: diagnose
description: Find the cause of an Open Revoke failure (error page, 4xx/5xx, stuck or failed Temporal workflow, sync or offboarding action that did nothing, wrong data in the panel, browser connector failing in the shared Chromium) before changing code, then make the smallest repair. Inside website/ its own diagnose skill wins.
---

# Diagnose, then fix

Find the cause first. A repair made on a guess hides the evidence that would show the guess wrong.

## Locate the cause (read-only)

1. Write down the symptom, the expected result and what runs: `dock status`. Code on disk
   does not prove the container is current (`api` and `web` reload, `worker` restarts on each
   `.py` change; a new dependency needs `dc restart api worker` or `dc restart web`).
2. Trace the request boundary by boundary:
   - panel: `shot web /<path>` prints console errors and failed requests.
   - `web` proxies `/api/...` to `api` (`frontend/src/lib/api/`), router in
     `backend/app/api/`, logic in `backend/app/services/`, rows via `dc exec postgres psql -U postgres -d open_revoke -c "<query>"`.
   - async: service starts a Temporal workflow (`backend/app/temporal/`), activities call
     services and connectors; `dc logs --tail 200 worker`.
   - connectors: `backend/app/connectors/<app>/`; browser connectors drive the `browser`
     container over CDP, watch it live on http://localhost:18412/vnc.html.
   - e-mail: Mailpit on http://localhost:18413.
3. The first boundary with wrong state is the cause. Everything after it is a consequence.
4. Library or vendor behaviour (FastAPI, Temporal, Next.js 16, an app's API) comes from its
   docs or `open-revoke/docs/connectors/`, not memory. Next.js 16: `node_modules/next/dist/docs/`.

Allowed while looking: a temporary log line or probe script. Remove it before the repair.
Not allowed: `docker compose down -v`, rerunning a write action with an unknown outcome on a
real account, restarting other projects' containers.

## Repair

1. State the cause and the files the repair touches, one line each. A repair that grows past
   them means the diagnosis was wrong: go back.
2. Make the smallest change that removes the cause; follow the feature skill in
   `open-revoke/skills/`.
3. Reproduce the original symptom and show it gone in the stack. No automated tests (repo
   `AGENTS.md`, Development mode).
4. Finish with [verify](../verify/SKILL.md).

No cause found is a valid result: list the boundaries ruled out and the evidence missing.
