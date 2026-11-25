/** Pages without the panel frame. Guest-only pages send a signed-in user on to the panel. */
export const GUEST_ONLY_ROUTES = ["/login", "/setup", "/register", "/signup", "/forgot-password"];
export const PUBLIC_ROUTES = [...GUEST_ONLY_ROUTES, "/reset-password"];
/** Home of a `user` (not admin): My access. */
export const USER_HOME = "/me";
/** Signed-in pages in the sign-in frame (no sidebar): the questions right after the first-run setup. */
export const FRAMELESS_ROUTES = ["/welcome"];

export function isRoute(pathname: string, routes: readonly string[]): boolean {
  return routes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

/** `?next=` target after sign-in: only a path inside the panel, never another site. */
export function safeNext(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return "/";
  return isRoute(value, PUBLIC_ROUTES) ? "/" : value;
}

/** A user (not admin) may open only My access, their own account settings and API tokens (not users or the agent). */
const USER_PAGES = ["/settings", "/settings/two-factor", "/settings/api", "/settings/api/new"];
export function userRedirect(pathname: string): string | null {
  return USER_PAGES.includes(pathname) || isRoute(pathname, [USER_HOME]) ? null : USER_HOME;
}
