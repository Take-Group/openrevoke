# Skill: click recipes (writes in apps without an API)

Decision, format and safety rules: `docs/browser-recipes.md`.

## What it does

A browser connector reads accounts with `fetch()` in the panel tab, but
writes (invite, remove) by clicking through the app's admin page like a
person. The steps are a JSON recipe, not code. A deterministic runner
executes them; no language model runs during a write.

## Files

| File | Role |
|---|---|
| `backend/app/recipes/model.py` | `Recipe`, `Step`, `Locator`; `load_recipe` (cached, validated), `render_steps` (`{{param}}`), `config_params`; `RecipeError`, `RecipeStepError` |
| `backend/app/browser/recipe_runner.py` | `run_steps`: new tab, local fixes then candidates, exactly one visible match, 10 s wait, AI repair through `RecipeSupport`, screenshot on failure, tab closed after |
| `backend/app/recipes/repair.py` | `RecipeSupport` protocol, `Alternative` (within + target), `Probe`, `RepairRequest`, `Repair` |
| `backend/app/services/recipe_repair.py` | `RecipeRepairService`: the AI loop (`try_locator`, `use_locator` on the live page), stores `RecipeFix` |
| `backend/app/services/recipe_fixes.py`, `api/recipe_fixes.py` | active fixes for a run; list, approve, reject (revert) |
| `backend/app/browser/session.py` | `CdpBrowserSession.run_recipe` (protocol in `connectors/browser_api.py`) |
| `backend/app/services/action_execution.py` | `RecipeStepError` becomes "The click recipe stopped at step N ..." on the action |
| `backend/app/connectors/browser_fake/recipe.json` | reference recipe |
| `backend/app/connectors/slack/recipe.json` | first real recipe: Slack invite and deactivate by `data-qa` attributes |
| `backend/app/connectors/browser_fake/admin_page.py`, `api/dev_panel.py` | fake admin page `/api/dev/fake-panel/admin`, look switch `/ui?version=1|2` |

## Data flow

Action approved -> `ExecuteActionWorkflow` -> `connector.delete_account`
-> `ctx.browser.run_recipe(load_recipe(path), "delete_account", params,
origin=panel_url)` -> steps in a new tab -> the action's read-back
(`list_accounts`) confirms or fails the action.

Params: `config_params(ctx.config)` (non-secret config fields) plus the
action's `email`, `external_id`, `role`.

## Add a recipe to a connector

1. Sign in to the app in the shared browser (Browser page or noVNC).
2. Find roles and accessible names: Chrome DevTools > Accessibility, or
   `take_snapshot` of the `open-revoke-browser` MCP server.
3. Write `recipe.json` next to the connector. Give every step a stable
   `id` (local fixes pin to it; never reuse an id for another step). Put
   language-independent candidates first (`test_id`, `css` on a stable
   attribute), `role` + `name` in several languages last,
   scope row buttons with `within` (row that `has_text` `{{email}}`), put an
   `expect` with `{{email}}` before the irreversible click.
4. Call `run_recipe` from `create_account` / `delete_account`; keep reads on
   `fetch()`.
5. Run it on a test account only and check the action ends `done`.

## Check it on the fake panel

1. Log in to the fake panel in the shared browser, create an app with
   connector `browser_fake`, sync, switch on "Allow writes".
2. Delete or invite an account: the action ends `done`.
3. `curl http://localhost:18411/api/dev/fake-panel/ui?version=2`,
   run a delete: the action ends `failed` with the step and the candidate
   counts. Switch back with `?version=1`.

## When a step finds nothing

1. The runner tries the step's active local fixes (`recipe_fix`, newest
   first), then the recipe's candidates.
2. Nothing matches and the write has a `RecipeSupport` (every action write
   has one): `RecipeRepairService` asks the model from Settings > AI. It gets
   the goal, the recipe's purpose (remove: Remove, Deactivate, Suspend...),
   what the candidates found, the run values and the page's aria snapshot,
   and tests locators with `try_locator`; `use_locator` is checked again
   (exactly one visible element; an `expect` must still contain its text and
   be smaller than 2000 characters). At most 3 repairs per run.
3. An ordinary step: the fix is stored `active` (with `{{param}}` in place of
   the e-mail) and the run goes on. An irreversible click or any step of a `delete_account` recipe (page
   text could steer the model to another row): stored `proposed`,
   the run stops; the admin approves it ("Review fix" on the action) and
   presses "Retry". An `expect` that finds its element without the person's
   name is never repaired: that is the safety stop.
4. Any failure keeps a PNG of the tab (`action_screenshot`, "Where it
   stopped" on the action). "Revert AI fix" sets a fix to `rejected`.

Without AI settings the step fails with "AI repair is off".

## Not built yet

Recipe versions in the database with a diff (7d: today a fix is one locator
per step id, no editing by hand). A page of all fixes per app (the API
`GET /api/recipe-fixes` exists; the panel shows fixes only on the actions
that made them). Slack (7e) is done: invite, revoke and deactivation ran on
a real workspace.
