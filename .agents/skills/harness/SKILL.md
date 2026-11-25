---
name: harness
description: Write or change Open Revoke agent instructions - AGENTS.md files and folder maps, skills in open-revoke/.agents/skills, feature skills in open-revoke/skills, subagent profiles in .claude/agents and .codex/agents, and the harness in .agents/harness (hook, check). Use when a map is stale, a new folder or skill is needed, or an agent kept searching for something a map should have named. Inside website/ its own harness skill wins.
---

# Agent harness

## How it works

- `.agents/harness/hook.py` (Claude Code `PreToolUse`, set in the repo root
  `.claude/settings.json`): on the first touch of a folder it injects every `AGENTS.md` from the
  repo root down to that folder, once per session. Folders with a `CLAUDE.md` bridge (repo root,
  `open-revoke/`, `website/`) are skipped: Claude Code loads those itself.
- `.agents/harness/agent.py`: `context` (first command of a Codex session), `instructions <path>`
  (the chain the hook would inject), `check`.
- `.agents/harness/check.py`: fails on a folder under `open-revoke/` with 5+ entries and no map,
  a map naming a missing file or missing a file, a broken link or backticked path, a budget
  overrun, a skill without a row in the "Task to skill" table, a Claude profile without a Codex twin.
- `.claude/hooks/ruff-python.sh` (`PostToolUse`): formats and autofixes each edited backend `.py`.

## Where things go

- Repo-wide rules: repo root `AGENTS.md`. Product rules: `open-revoke/AGENTS.md`. Area facts: the
  area's `AGENTS.md`. `CLAUDE.md` exists only as the one-line bridge `@AGENTS.md` in the repo
  root, `open-revoke/` and `website/`.
- Folder map: in the folder's `AGENTS.md`, the whole file under `# <folder>/` or a `## Files`
  section beside rules. One bullet per entry, names in backticks: `- \`file.py\`: what it owns`.
  A folder under 5 entries has no map; the parent's bullet names its files.
- Procedures an agent repeats (explore, verify, diagnose): `open-revoke/.agents/skills/<name>/SKILL.md`,
  the only source; `open-revoke/.claude/skills` is a symlink to it. Add a row to the "Task to
  skill" table of `open-revoke/AGENTS.md`.
- How one feature works (files, data flow, how to extend): `open-revoke/skills/backend/` or
  `open-revoke/skills/frontend/`, listed in `open-revoke/AGENTS.md`.
- Subagent: thin twins `.claude/agents/<name>.md` and `.codex/agents/<name>.toml` naming the
  same `SKILL.md` and its `Subagent` section.

## Write

- English. Only what changes decisions: entry points, symbols, commands, the order that
  matters, pitfalls. A map line answers "do I need to open this file?" with the key symbols,
  not a restatement of the file name.
- No dates in `AGENTS.md` outside `docs/`. A backticked path must exist.
- Budgets: repo root, `open-revoke/` and `website/` `AGENTS.md` 10 KiB, any other `AGENTS.md`
  6 KiB (the hook injects it whole), `SKILL.md` 4 KiB.

## Verify

1. `python3 .agents/harness/agent.py check` from the repo root.
2. `python3 .agents/harness/agent.py instructions <path>` shows what an agent gets for a path.
3. Finish with [verify](../verify/SKILL.md).
