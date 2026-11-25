"""Which API operations become MCP tools and how clients should treat them.

Every route a panel user reaches with an API token is a tool by default (``catalog.py``): a new
endpoint shows up in the MCP server without a change here. Edit this file only to keep an
operation out or to mark one as destructive.
"""

# Operations a user reaches with a token but that make no sense for an AI assistant, or must not
# pass through one.
EXCLUDED: dict[str, str] = {
    "reveal_action_secret": "a temporary password must not go to a language model provider; the panel shows it",
    "set_slack_avatar": "an image upload; set it in the panel",
    "start_slack_oauth": "a browser redirect to Slack; use the panel",
    "finish_slack_oauth": "Slack's redirect back to the panel, not a call to make",
}

# Public operations (no sign-in) that are still useful to an assistant. Other public routes
# (sign-in, OAuth callbacks, logos, the fake panel) stay out.
PUBLIC_ALLOWED: frozenset[str] = frozenset({"list_catalog_apps", "list_currencies"})

# Beyond DELETE: operations that remove accounts in other apps or lock someone out. Clients
# (Claude Code, Codex) ask before such a call unless the user allowed it.
DESTRUCTIVE: frozenset[str] = frozenset(
    {
        "offboard_person",
        "approve_action",
        "approve_action_batch",
        "retry_action",
        "reset_user_totp",
        "approve_recipe_fix",
    }
)

# Tag of operations whose router has none.
DEFAULT_TAG = "system"
