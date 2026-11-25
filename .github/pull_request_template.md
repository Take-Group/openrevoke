## What and why

<!-- What changes, and the reason. Link the issue: "Closes #123". -->

## How I checked it

<!-- What you ran in the stack: the page you opened, the endpoint you called, the sync or action you ran. -->

- [ ] Backend: `uv run ruff check .` and `uv run ruff format --check .`
- [ ] Panel: `bun run lint`, `bun run typecheck` and `bun run build`
- [ ] ShellCheck, if `deploy/` or `scripts/` changed
- [ ] Checked by hand in the running stack (describe above)

## Checklist

- [ ] `CHANGELOG.md` has a line under `[Unreleased]` (or: the change is not visible to people who run Open Revoke)
- [ ] Models changed: an Alembic migration is in `backend/migrations/versions/`, reviewed by hand (renames use `op.alter_column`, `downgrade()` empty, no app model imports), and `uv run alembic check` passes
- [ ] API changed: `docs/openapi.json` and `frontend/src/lib/api/types.ts` are updated
- [ ] No secrets, `.env`, `captures/`, screenshots of real admin panels or real people's data in the diff or the description
- [ ] The change is mine to license under MIT (code outside `ee/`)
