from fastapi import APIRouter, Depends

from app.api.access_requests import router as access_requests_router
from app.api.accounts import router as accounts_router
from app.api.actions import router as actions_router
from app.api.ai import router as ai_router
from app.api.api_tokens import router as api_tokens_router
from app.api.apps import router as apps_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.auth_deps import get_current_session, get_current_user, require_admin
from app.api.browser import public_router as browser_policy_router
from app.api.browser import router as browser_router
from app.api.browser_live import router as browser_live_router
from app.api.catalog import public_router as catalog_public_router
from app.api.connections import router as connections_router
from app.api.currencies import public_router as currencies_public_router
from app.api.currencies import router as currencies_router
from app.api.dashboard import router as dashboard_router
from app.api.dev_panel import router as dev_panel_router
from app.api.discovery import router as discovery_router
from app.api.errors import ERROR_RESPONSES
from app.api.google_cloud_setup import router as google_cloud_setup_router
from app.api.google_oauth import callback_router as google_oauth_callback_router
from app.api.google_oauth import router as google_oauth_router
from app.api.health import router as health_router
from app.api.me import router as me_router
from app.api.people import router as people_router
from app.api.recipe_fixes import router as recipe_fixes_router
from app.api.setup_checklist import router as setup_checklist_router
from app.api.slack_agent import router as slack_agent_router
from app.api.system import router as system_router
from app.api.users import router as users_router

# Panel API under /api. Every route needs a signed-in admin
# (skills/backend/auth.md); sign-in itself is in auth_router. A user (not admin) reaches only me_router.
domain_router = APIRouter(prefix="/api", responses=ERROR_RESPONSES, dependencies=[Depends(require_admin)])
domain_router.include_router(dashboard_router, tags=["dashboard"])
domain_router.include_router(setup_checklist_router, tags=["onboarding"])
domain_router.include_router(people_router, tags=["people"])
domain_router.include_router(discovery_router, tags=["discovery"])
domain_router.include_router(google_oauth_router, tags=["discovery"])
domain_router.include_router(google_cloud_setup_router, tags=["discovery"])
domain_router.include_router(apps_router, tags=["apps"])
domain_router.include_router(accounts_router, tags=["accounts"])
domain_router.include_router(connections_router, tags=["connections"])
domain_router.include_router(actions_router, tags=["actions"])
domain_router.include_router(recipe_fixes_router, tags=["actions"])
domain_router.include_router(browser_router, tags=["browser"])
domain_router.include_router(audit_router, tags=["audit"])
domain_router.include_router(users_router, tags=["users"])
domain_router.include_router(ai_router, tags=["ai"])
domain_router.include_router(slack_agent_router, tags=["slack"])
domain_router.include_router(access_requests_router, tags=["access-requests"])
domain_router.include_router(currencies_router)
domain_router.include_router(system_router)

# The signed-in user's own access: every role, with the cookie or an API token.
self_router = APIRouter(prefix="/api", responses=ERROR_RESPONSES, dependencies=[Depends(get_current_user)])
self_router.include_router(me_router, tags=["me"])

# The signed-in user's API tokens: every role, the panel session only (a token cannot manage tokens).
session_router = APIRouter(prefix="/api", responses=ERROR_RESPONSES, dependencies=[Depends(get_current_session)])
session_router.include_router(api_tokens_router, tags=["api-tokens"])

# Fake admin panel for the browser_fake connector; 404 unless the fake connectors are enabled.
# No sign-in: the shared browser opens it, without the panel's session.
dev_router = APIRouter(prefix="/api")
dev_router.include_router(dev_panel_router)

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(currencies_public_router)
api_router.include_router(catalog_public_router)
# The browser container polls this (no session) for which password manager to force-install.
api_router.include_router(browser_policy_router, tags=["browser"])
api_router.include_router(google_oauth_callback_router)
# Live view of the shared browser: checks the session itself (also for the WebSocket), admins only.
api_router.include_router(browser_live_router)
api_router.include_router(self_router)
api_router.include_router(session_router)
api_router.include_router(domain_router)
api_router.include_router(dev_router)
