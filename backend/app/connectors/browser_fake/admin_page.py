"""HTML admin page of the fake panel: users table, row menu, confirmation and invite dialogs.

The ``browser_fake`` click recipe (``recipe.json``) writes through this page.
Version 2 renames every button, so a recipe recorded on version 1 fails the
way it would after a real redesign. Served by ``app/api/dev_panel.py``.
"""

from html import escape
from typing import Any

LABELS = {
    1: {"invite": "Invite", "menu": "Actions", "remove": "Remove", "confirm": "Remove", "send": "Send invite"},
    2: {"invite": "Add member", "menu": "More", "remove": "Deactivate user", "confirm": "Deactivate", "send": "Add"},
}

SCRIPT = """<script>
const base = %(base)s, count = %(count)s, csrf = {"X-CSRF-Token": "fake-csrf-token"};
let pending = null;
document.querySelectorAll("[data-menu]").forEach(button => button.addEventListener("click", () => {
  const menu = document.getElementById("menu-" + button.dataset.menu);
  menu.hidden = !menu.hidden;
  button.setAttribute("aria-expanded", String(!menu.hidden));
}));
document.querySelectorAll("[data-remove]").forEach(item => item.addEventListener("click", () => {
  pending = item.dataset.remove;
  document.getElementById("confirm-email").textContent = item.dataset.email;
  item.closest("[role=menu]").hidden = true;
  document.getElementById("confirm").showModal();
}));
document.getElementById("confirm-ok").addEventListener("click", async () => {
  await fetch(`${base}/users/${pending}/remove?count=${count}`, {method: "POST", headers: csrf});
  location.reload();
});
document.getElementById("invite-open").addEventListener("click", () => document.getElementById("invite").showModal());
document.getElementById("invite-send").addEventListener("click", async () => {
  const email = document.getElementById("invite-email").value;
  await fetch(`${base}/users?count=${count}`, {
    method: "POST", headers: {...csrf, "Content-Type": "application/json"}, body: JSON.stringify({email}),
  });
  location.reload();
});
document.querySelectorAll("[data-close]").forEach(b => b.addEventListener("click", () => b.closest("dialog").close()));
</script>"""

STYLE = """<style>
body{font-family:sans-serif;margin:3rem;max-width:56rem}
table{border-collapse:collapse;width:100%;margin-top:1rem}
td,th{border-bottom:1px solid #ddd;padding:.5rem;text-align:left}
[role=menu]{position:absolute;background:#fff;border:1px solid #ccc;padding:.25rem}
[role=menu] button{display:block;width:100%}dialog{padding:1.5rem}
</style>"""


def render_admin_page(users: list[dict[str, Any]], *, version: int, base: str, count: int) -> str:
    labels = LABELS[version]
    rows = "\n".join(_row(user, labels) for user in users)
    script = SCRIPT % {"base": f'"{base}"', "count": count}
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Users - Fake panel</title>{STYLE}</head><body>
<h1>Users</h1>
<button id="invite-open" type="button">{labels["invite"]}</button>
<table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead>
<tbody>
{rows}
</tbody></table>
<dialog id="confirm" aria-labelledby="confirm-title">
  <h2 id="confirm-title">{labels["remove"]}</h2>
  <p>{labels["remove"]} <strong id="confirm-email"></strong> from the workspace?</p>
  <button type="button" data-close>Cancel</button>
  <button type="button" id="confirm-ok">{labels["confirm"]}</button>
</dialog>
<dialog id="invite" aria-labelledby="invite-title">
  <h2 id="invite-title">{labels["invite"]}</h2>
  <label>Email <input id="invite-email" type="email"></label>
  <button type="button" data-close>Cancel</button>
  <button type="button" id="invite-send">{labels["send"]}</button>
</dialog>
{script}
</body></html>"""


def _row(user: dict[str, Any], labels: dict[str, str]) -> str:
    user_id = escape(str(user["id"]))
    email = escape(str(user.get("email") or ""))
    return (
        f"<tr><td>{escape(str(user.get('name') or ''))}</td><td>{email}</td>"
        f"<td>{escape(str(user.get('role') or ''))}</td><td>{escape(str(user.get('state') or ''))}</td>"
        f'<td><button type="button" aria-haspopup="menu" aria-expanded="false" data-menu="{user_id}">'
        f"{labels['menu']}</button>"
        f'<div role="menu" id="menu-{user_id}" hidden>'
        f'<button type="button" role="menuitem" data-remove="{user_id}" data-email="{email}">'
        f"{labels['remove']}</button>"
        "</div></td></tr>"
    )
