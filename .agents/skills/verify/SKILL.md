---
name: verify
description: Verify a finished Open Revoke product change (ruff, lint, typecheck, harness check, a run in the local stack) and commit it locally. Use at the end of every change in open-revoke/ (backend, frontend, docs, skills, AGENTS.md maps). Inside website/ its own verify skill wins.
---

# Verify and commit

Every larger change ends with a local commit, without waiting to be asked (repo `AGENTS.md`,
Git). This skill is that step.

1. `git status` and the diff against the task scope. Other sessions work in this clone: their
   uncommitted files are not yours. Unsure who owns a change: ask (`ListAgents`, `SendMessage`).
2. Run the checks of the touched areas, from the repo root:

   | Area | Check |
   | --- | --- |
   | `open-revoke/backend` | `dc exec api ruff check .` and `dc exec api ruff format --check .` |
   | `open-revoke/frontend` | `dc exec web bun run lint` and `dc exec web bun run typecheck` |
   | endpoint or schema | refresh `open-revoke/docs/openapi.json` and `frontend/src/lib/api/types.ts` (`open-revoke/AGENTS.md`, Checks) |
   | model | `dc exec api python -m app.db reset`, then the seeded data shows in the panel |
   | any added, moved or deleted file, `AGENTS.md`, skill | `python3 .agents/harness/agent.py check` (fails on a stale folder map) |

3. Run the changed behaviour by hand in the stack: `curl` the endpoint on
   `http://localhost:18411` (mutations need `X-Open-Revoke-Client: 1` and a
   session cookie), run the workflow and read `dc logs --tail 100 worker`, or open the screen with
   `shot web /<path>`. Clean lint is not runtime acceptance. Report every check you could not run.
4. A file added, moved or deleted: its folder's `AGENTS.md` map changes in the same commit. A
   changed feature: its skill in `open-revoke/skills/` too.
5. Review the diff: scope, secrets (`.env`, keys), debug leftovers, files over 600 lines.
6. Stage only your files by name (`git add <paths>`, never `-A`), then `git diff --cached --check`.
7. Commit one logical change on `main`, message in English: what changed and why. No AI
   attribution lines. No push.

Report the change, the checks with results, what stays unproven and the commit SHA.
