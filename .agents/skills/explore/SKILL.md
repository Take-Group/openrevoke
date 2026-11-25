---
name: explore
description: Delegate read-only code exploration of the Open Revoke product (open-revoke/backend, open-revoke/frontend) to the open-revoke-explore subagent before the first edit in an unfamiliar area. Use when a change spans backend and frontend or needs three or more unread files. Skip for files already read in this session and for web research. Inside website/ its own explore skill wins.
---

# Code exploration

Start from the folder maps: every folder with 5+ files has an `AGENTS.md` that names each file
and its key symbols. Often the map alone tells you which two files to open; then skip the
subagent and read them.

## Main agent

1. Give one `subagent_type="open-revoke-explore"` subagent (profile in the repo root
   `.claude/agents/`, Haiku, 20 turns) the task, the questions, the checkout root and the
   constraints. No session history, no whole files. Pass no `model`: it overrides the profile.
2. One scope per run that fits about twenty tool calls (backend + frontend is two runs).
3. Do not read the same files meanwhile. Do independent work.
4. If a run hit its limit with nothing returned, read the scope yourself.
5. Send follow-ups to the same subagent (SendMessage).
6. Read the returned code before implementing, then the feature skill in `open-revoke/skills/`
   that `open-revoke/AGENTS.md` lists for the area.

## Subagent

Read-only: no delegation, web research, edits or running services. Read `open-revoke/AGENTS.md`,
then walk the `AGENTS.md` maps folder by folder down to the files; never list folders to learn
what they hold. Trace callers and contract consumers, not just names: an endpoint schema reaches
`open-revoke/docs/openapi.json`, `frontend/src/lib/api/types.ts` and the hooks in
`frontend/src/hooks/`; a model reaches `backend/app/db/seed.py`; a connector reaches
`backend/app/connectors/registry.py` and the sync workflow.

Grep and read the named lines, never whole modules. Build the handoff as you go and report
before the budget runs out: a partial map with `path:line` beats nothing.

Handoff in English, under 800 words, `path:line` and symbol names with one-line reasons:
- entry point and execution flow.
- files and symbols to read or change, in order.
- contracts, consumers, patterns to copy, the feature skill to follow.
- confirmed findings apart from hypotheses and open questions.
- maps that were wrong or missing (the main agent fixes them).
