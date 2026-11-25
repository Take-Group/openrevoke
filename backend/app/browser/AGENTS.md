# open-revoke/backend/app/browser/

The shared Chromium (container `browser`, over CDP with Playwright) for browser connectors, and the live view of it. Connectors see only the protocol in `connectors/browser_api.py`. Never call `browser.close()` on a CDP connection (it can close the real browser); `disconnect` only drops the WebSocket.

- `__init__.py`: docstring only.
- `provider.py`: `BrowserProvider` protocol (`connect`, `live_view_url`, `health`, `tabs`, `disconnect`), `LocalChromiumProvider` (one lazy connection per process under a lock, resolves the host to an IP because DevTools rejects other Host names), `BrowserHealth`, `TabInfo`, `get_browser_provider()`.
- `session.py`: `CdpBrowserSession` (optional `recipe_support` for writes): one tab per origin; `fetch()` runs inside the panel's tab so cookies and origin come along; `open`, `open_tab`, `cookies`, `local_storage`, `evaluate`, `captured_header`, `run_recipe`; `open_browser_session()`.
- `recipe_runner.py`: `run_steps` runs a rendered click recipe in a new tab (closed after): local fixes, then the step's candidates; the first with exactly one visible element wins, waits up to 10 s; a step that finds nothing asks `RecipeSupport.repair` (at most 3 per run; an irreversible click stops for an admin); raises `RecipeStepError` (with a screenshot) or `NeedsLogin`.
- `capture.py`: `HeaderCapture`: last auth headers (`authorization`, csrf, `x-slack-*`) per host, in memory for one hour, never logged or returned; `is_auth_header`.
- `live_proxy.py`: `fetch_file` (only `live.html` and noVNC modules), `pipe(websocket)` to `websockify` in the container; used by `api/browser_live.py`.
