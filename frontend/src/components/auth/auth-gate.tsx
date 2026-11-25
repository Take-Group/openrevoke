"use client";

import { Loader2Icon } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";

import { AuthShell } from "@/components/auth/auth-shell";
import {
  FRAMELESS_ROUTES,
  GUEST_ONLY_ROUTES,
  PUBLIC_ROUTES,
  isRoute,
  safeNext,
  userRedirect,
} from "@/components/auth/routes";
import { InlineError } from "@/components/common/notice";
import { AdminLayout } from "@/components/layout/admin-layout";
import { Button } from "@/components/ui/button";
import { useAuthState } from "@/hooks/use-auth";
import { errorMessage } from "@/lib/api/client";
import { setAppTimeZone } from "@/lib/date-time";
import type { AuthState } from "@/lib/api/auth-types";

/** Where this path must go for this auth state, or null to stay. */
function redirectFor(pathname: string, state: AuthState): string | null {
  if (state.setup_required) return pathname === "/setup" ? null : "/setup";
  // A new installation goes on to two questions: where people come from, where the team talks.
  if (pathname === "/setup") return state.user ? "/welcome" : "/login";
  if (state.user) {
    const admin = state.user.role === "admin";
    if (isRoute(pathname, GUEST_ONLY_ROUTES)) {
      const next = safeNext(new URLSearchParams(window.location.search).get("next"));
      return admin ? next : (userRedirect(next) ?? next);
    }
    if (isRoute(pathname, PUBLIC_ROUTES)) return null;
    return admin ? null : userRedirect(pathname);
  }
  if (isRoute(pathname, PUBLIC_ROUTES)) return null;
  const here = `${pathname}${window.location.search}`;
  return here === "/" ? "/login" : `/login?next=${encodeURIComponent(here)}`;
}

/**
 * True while a TOTP step is on screen. The account already exists then, so a
 * refetched auth state would send /setup or /register away and lose the QR code.
 */
const SignInFlow = createContext<(active: boolean) => void>(() => {});

/** Call in a sign-in step: the gate does not redirect while it is mounted. */
export function useHoldSignInPage() {
  const setActive = useContext(SignInFlow);
  useEffect(() => {
    setActive(true);
    return () => setActive(false);
  }, [setActive]);
}

function FullScreen({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-svh items-center justify-center p-6">{children}</div>;
}

/**
 * Decides what a page shows: the first-run setup, the sign-in pages (without
 * the sidebar), or the panel. The API enforces the session anyway; this only
 * keeps the user on the right page.
 */
export function AuthGate({ sidebarOpen, children }: { sidebarOpen: boolean; children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const auth = useAuthState();
  const [holding, setHolding] = useState(false);
  const signedIn = Boolean(auth.data?.user);
  const target = auth.data && (!holding || signedIn) ? redirectFor(pathname, auth.data) : null;
  // Dates in the panel use the organization's time zone. Set during render, before the children format anything.
  setAppTimeZone(auth.data?.organization?.timezone);

  useEffect(() => {
    if (target && target !== pathname) router.replace(target);
  }, [target, pathname, router]);

  if (auth.isError) {
    return (
      <FullScreen>
        <div className="flex flex-col items-start gap-3">
          <InlineError message={errorMessage(auth.error)} />
          <Button variant="outline" size="sm" onClick={() => auth.refetch()}>
            Try again
          </Button>
        </div>
      </FullScreen>
    );
  }
  if (!auth.data || target) {
    return (
      <FullScreen>
        <Loader2Icon className="size-5 animate-spin text-muted-foreground" aria-label="Loading" />
      </FullScreen>
    );
  }
  if (isRoute(pathname, PUBLIC_ROUTES) || isRoute(pathname, FRAMELESS_ROUTES)) {
    return (
      <SignInFlow.Provider value={setHolding}>
        <AuthShell>{children}</AuthShell>
      </SignInFlow.Provider>
    );
  }
  // Keyed by the time zone: after a change in Settings every date is formatted again.
  return (
    <AdminLayout key={auth.data.organization?.timezone} defaultOpen={sidebarOpen}>
      {children}
    </AdminLayout>
  );
}
