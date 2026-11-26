---
name: ship
description: Publish verified local commits of open-revoke/ to GitHub through a pull request, with a Macroscope review when the change is worth it, and merge after the review. Use for every push of the product repo (close-out, "wypchnij", "push"). Never push to main directly.
---

# Ship through a pull request

Changes reach `main` of `Take-Group/openrevoke` only through a pull request. The repo is public:
read the diff for secrets, names and private plans before you push anything.

Macroscope (GitHub App `macroscope-app`) reviews pull requests for bugs. In this repo it runs only
when asked (Correctness: manual invocation only). It costs $0.05 per KB of diff (Balanced mode),
at least $0.50 per review, paid from a shared prepaid balance. Ask for a review only when it can
find something.

1. Start from verified local commits (skill [verify](../verify/SKILL.md)). Group them by topic:
   one pull request per logical change. Fetch first: `git fetch origin`, then
   `git rebase origin/main`.
2. Push a branch, not `main`: `git push origin HEAD:refs/heads/<topic>`, where `<topic>` is a short
   kebab-case name of the change (no agent or tool names). Open the pull request:
   `gh pr create --repo Take-Group/openrevoke --base main --head <topic> --title "<title>" --body "<what and why, what you checked>"`.
3. Decide on a review. Diff size: `gh pr diff <n> | wc -c` (1024 bytes = 1 KB).

   | Change | Macroscope |
   | --- | --- |
   | code in `backend/app`, `frontend/src`, `deploy/`, `docker/`, `scripts/`, `.github/workflows` | yes |
   | security code (auth, sessions, secrets, connectors, actions, tokens), any size | yes |
   | only docs, `AGENTS.md`, skills, comments, translations, typo, version bump | no |
   | diff over 200 KB (over $10) | ask Bartek first, or split the pull request |

   To review: `gh pr comment <n> --body "@macroscope-app review this PR"` (exactly this; a bare
   "@macroscope-app review" is read as a question and starts no review). The review is the check
   run "Macroscope - Correctness Check"; an "Approvability Check" marked skipped is expected.
4. Wait for the result. CI and the review are check runs: `gh pr checks <n> --watch`. Read the
   comments: `gh api repos/Take-Group/openrevoke/pulls/<n>/comments` and `gh pr view <n> --comments`.
5. Judge every finding: reproduce it or read the code. A real bug: fix it in a new commit on the
   same branch (skill verify, then push the branch) and reply in the thread with the fix. A false
   positive: reply why and resolve. Do not ask for another review after small fixes; ask again
   only when the fix changes the design.
6. Merge when CI is green and no real finding is open:
   `gh pr merge <n> --repo Take-Group/openrevoke --rebase --delete-branch`. Then
   `git pull --rebase origin main`: the rebase drops your local commits that are now on `main`
   and keeps unpushed commits of other sessions on top. Never `git reset --hard`.

Never merge a pull request with an open real finding, never let Macroscope merge its own fix pull
requests, and never push to `main` to skip the review.

Report the pull request URL, whether Macroscope ran and why, each finding with your verdict, and
the merge commit.
