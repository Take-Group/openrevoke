# open-revoke/backend/app/connectors/browser_fake/

The `browser_fake` connector: the app's own fake admin panel (`app/api/dev_panel.py`) through the real shared browser, listed only in development. Reads with `fetch()` in the panel tab; writes with the click recipe (`skills/backend/click-recipes.md`). State lives in Redis.

- `__init__.py`: empty.
- `connector.py`: `BrowserFakeConnector`, `BrowserFakeConfig` (`panel_url`, `accounts`, `page_size`); `create_account` and `delete_account` call `ctx.browser.run_recipe`, invite reads the new account back.
- `recipe.json`: click recipe with `create_account` and `delete_account` steps on the `/admin` page.
- `admin_page.py`: `render_admin_page` (users table, row "Actions" menu, confirmation and invite dialogs); `LABELS` version 2 renames every button to break the recipe on purpose.
- `mapping.py`: `panel_users(count)` (fictional users), `panel_page`, `parse_page`, `user_to_account`.
- `panel_state.py`: invited and removed users (`current_users`, `invite`, `remove`) and the page look (`ui_version`, `set_ui_version`) in Redis.
