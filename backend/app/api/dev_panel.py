"""Fake admin panel for the ``browser_fake`` connector. Development only.

Exists only when the fake connectors are enabled (``DEBUG`` or
``OPEN_REVOKE_ENABLE_FAKE_CONNECTOR``); otherwise every route answers 404.
Not part of the API contract (hidden from OpenAPI). The browser container
opens it at ``http://open-revoke-app:8000/api/dev/fake-panel``.
"""

from typing import Annotated

from fastapi import APIRouter, Body, Cookie, HTTPException, Query, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.connectors.browser_fake import panel_state
from app.connectors.browser_fake.admin_page import render_admin_page
from app.connectors.browser_fake.mapping import panel_page, panel_users
from app.connectors.registry import fake_connector_enabled

PREFIX = "/dev/fake-panel"
COOKIE = "fake_panel_session"
COOKIE_VALUE = "logged-in"
COOKIE_MAX_AGE = 30 * 24 * 3600  # persistent, so it is written to the profile on disk

BASE = f"/api{PREFIX}"  # absolute links: the panel page has no trailing slash

router = APIRouter(prefix=PREFIX, include_in_schema=False)

SessionCookie = Annotated[str | None, Cookie(alias=COOKIE)]


def _require_enabled() -> None:
    if not fake_connector_enabled():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")


def _page(title: str, body: str) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:sans-serif;margin:3rem;max-width:40rem}}button{{font-size:1.1rem;padding:.5rem 1.5rem}}</style>
</head><body>{body}</body></html>"""
    return HTMLResponse(html)


@router.get("")
async def panel_home(session: SessionCookie = None) -> HTMLResponse:
    _require_enabled()
    if session != COOKIE_VALUE:
        return _page("Fake panel", f'<h1>Fake panel</h1><p>Not logged in.</p><p><a href="{BASE}/login">Log in</a></p>')
    # The page calls its own API with a CSRF header, like real panels, so header capture has something to see.
    script = f"""<script>
fetch("{BASE}/users?page=1&per_page=1", {{headers: {{"X-CSRF-Token": "fake-csrf-token"}}}})
  .then(r => r.json()).then(b => {{ document.getElementById("total").textContent = b.total; }});
</script>"""
    return _page(
        "Fake panel",
        '<h1>Fake panel</h1><p>Logged in. Users: <span id="total">…</span></p>'
        f'<p><a href="{BASE}/logout">Log out</a></p>{script}',
    )


@router.get("/login")
async def login_form() -> HTMLResponse:
    _require_enabled()
    return _page(
        "Log in to the fake panel",
        f'<h1>Log in</h1><form method="post" action="{BASE}/login"><button type="submit">Log in</button></form>',
    )


@router.post("/login")
async def login() -> RedirectResponse:
    _require_enabled()
    response = RedirectResponse(BASE, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(COOKIE, COOKIE_VALUE, max_age=COOKIE_MAX_AGE, path=BASE, httponly=True, samesite="lax")
    return response


@router.get("/logout")
async def logout() -> RedirectResponse:
    _require_enabled()
    response = RedirectResponse(f"{BASE}/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(COOKIE, path=BASE)
    return response


@router.get("/admin", response_model=None)
async def panel_admin_page(
    session: SessionCookie = None, count: Annotated[int, Query(ge=0, le=500)] = 5
) -> HTMLResponse | RedirectResponse:
    """Users table with buttons: the page the browser_fake click recipe writes through."""
    _require_enabled()
    if session != COOKIE_VALUE:
        return RedirectResponse(f"{BASE}/login", status_code=status.HTTP_303_SEE_OTHER)
    users = await panel_state.current_users(panel_users(count))
    version = await panel_state.ui_version()
    return HTMLResponse(render_admin_page(users, version=version, base=BASE, count=count))


@router.get("/ui")
async def panel_ui_version(version: Annotated[int | None, Query(ge=1, le=2)] = None) -> JSONResponse:
    """Read or switch the admin page look (``?version=2`` renames the buttons to break the recipe)."""
    _require_enabled()
    if version is not None:
        await panel_state.set_ui_version(version)
    return JSONResponse({"version": await panel_state.ui_version()})


@router.get("/users")
async def panel_users_page(
    session: SessionCookie = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 2,
    count: Annotated[int, Query(ge=0, le=500)] = 5,
) -> JSONResponse:
    _require_enabled()
    if session != COOKIE_VALUE:
        return _not_logged_in()
    users = await panel_state.current_users(panel_users(count))
    return JSONResponse(panel_page(users, page, per_page))


@router.post("/users")
async def panel_invite_user(
    email: Annotated[str, Body(embed=True)],
    role: Annotated[str | None, Body(embed=True)] = None,
    session: SessionCookie = None,
    count: Annotated[int, Query(ge=0, le=500)] = 5,
) -> JSONResponse:
    """Invite a user (the browser_fake connector's create_account)."""
    _require_enabled()
    if session != COOKIE_VALUE:
        return _not_logged_in()
    email = email.strip().lower()
    if any(user["email"] == email for user in await panel_state.current_users(panel_users(count))):
        return JSONResponse({"error": "already_member"}, status_code=status.HTTP_409_CONFLICT)
    return JSONResponse(await panel_state.invite(email, role), status_code=status.HTTP_201_CREATED)


@router.post("/users/{user_id}/remove")
async def panel_remove_user(
    user_id: str, session: SessionCookie = None, count: Annotated[int, Query(ge=0, le=500)] = 5
) -> JSONResponse:
    """Remove a user (the browser_fake connector's delete_account)."""
    _require_enabled()
    if session != COOKIE_VALUE:
        return _not_logged_in()
    if user_id not in {user["id"] for user in await panel_state.current_users(panel_users(count))}:
        return JSONResponse({"error": "user_not_found"}, status_code=status.HTTP_404_NOT_FOUND)
    await panel_state.remove(user_id)
    return JSONResponse({"ok": True})


def _not_logged_in() -> JSONResponse:
    return JSONResponse({"error": "not_logged_in"}, status_code=status.HTTP_401_UNAUTHORIZED)
