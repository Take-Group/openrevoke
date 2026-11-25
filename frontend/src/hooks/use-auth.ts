"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { apiGet, apiSend } from "@/lib/api/client";
import type { AuthState, AuthStep, ChangePasswordRequest, InviteInfo, LoginRequest, RegisterRequest, ResetPasswordRequest, SetupRequest, SignupRequest, SignupResult, TotpRequest, TotpSetupOut, UserOut } from "@/lib/api/auth-types";

/** Who is signed in, whether the first-run setup is needed, the organization. */
export function useAuthState() {
  return useQuery({
    queryKey: ["auth"],
    queryFn: () => apiGet<AuthState>("/api/auth/state"),
    staleTime: 60_000,
    retry: 1,
  });
}

// Sign-in steps show their errors inline in the form, so no toasts here. `authFlow`: their 401
// (wrong password or code) must not reset the auth state (providers.tsx).
const AUTH_FLOW = { authFlow: true };

export function useSetup() {
  return useMutation({ meta: AUTH_FLOW, mutationFn: (data: SetupRequest) => apiSend<AuthStep>("POST", "/api/auth/setup", data) });
}

/** Step `done` (no 2FA on the account): the cookie is set, so enter the panel; `totp`: the caller shows the code step. */
export function useLogin() {
  const enter = useEnterPanel();
  return useMutation({
    meta: AUTH_FLOW,
    mutationFn: (data: LoginRequest) => apiSend<AuthStep>("POST", "/api/auth/login", data),
    onSuccess: async (step) => {
      if (step.step === "done") await enter();
    },
  });
}

/** Invite registration signs in at once (step `done`). */
export function useRegister() {
  const enter = useEnterPanel();
  return useMutation({
    meta: AUTH_FLOW,
    mutationFn: (data: RegisterRequest) => apiSend<AuthStep>("POST", "/api/auth/register", data),
    onSuccess: enter,
  });
}

/** Self sign-up: `active` (approved domain) signs in on the sign-in page; `pending` waits for an admin. */
export function useSignup() {
  return useMutation({ meta: AUTH_FLOW, mutationFn: (data: SignupRequest) => apiSend<SignupResult>("POST", "/api/auth/signup", data) });
}

/** After the session cookie is set: drop the whole cache for the new user and refresh the auth state. */
export function useEnterPanel() {
  const queryClient = useQueryClient();
  return async () => {
    queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== "auth" });
    await queryClient.invalidateQueries({ queryKey: ["auth"] });
  };
}

/** Code step of a sign-in with 2FA (and of the first-run setup). On success the cookie is set. */
export function useVerifyTotp() {
  const enter = useEnterPanel();
  return useMutation({
    meta: AUTH_FLOW,
    mutationFn: (data: TotpRequest) => apiSend<UserOut>("POST", "/api/auth/totp", data),
    onSuccess: enter,
  });
}

/** Settings: a new secret and QR code to scan. */
export function useStartTwoFactor() {
  return useMutation({ meta: AUTH_FLOW, mutationFn: () => apiSend<TotpSetupOut>("POST", "/api/auth/2fa/setup") });
}

/** Settings: turn 2FA on with the first code, or off with a current one. Refreshes the signed-in user. */
export function useSetTwoFactor() {
  const queryClient = useQueryClient();
  return useMutation({
    meta: AUTH_FLOW, // a wrong code is 401 too
    mutationFn: (data: { on: true; ticket: string; code: string } | { on: false; code: string }) =>
      data.on
        ? apiSend<UserOut>("POST", "/api/auth/2fa/enable", { ticket: data.ticket, code: data.code })
        : apiSend<UserOut>("POST", "/api/auth/2fa/disable", { code: data.code }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["auth"] }),
  });
}

/** First-run setup: continue without 2FA from the `totp_setup` step; Settings can turn it on later. */
export function useSkipTotp() {
  const enter = useEnterPanel();
  return useMutation({
    meta: AUTH_FLOW,
    mutationFn: (ticket: string) => apiSend<UserOut>("POST", "/api/auth/totp/skip", { ticket }),
    onSuccess: enter,
  });
}

/** Is the token of a setup link valid? Checked before the form, so a stale link does not waste the typing. */
export function useSetupTokenCheck(token: string | null) {
  return useQuery({
    queryKey: ["auth", "setup-token", token],
    // 204 has no body, and React Query refuses `undefined` as data: answer `true` instead.
    queryFn: async () => {
      await apiSend<void>("POST", "/api/auth/setup/check", { token });
      return true;
    },
    enabled: Boolean(token),
    retry: false,
  });
}

export function useInviteInfo(token: string | null) {
  return useQuery({
    queryKey: ["auth", "invite", token],
    queryFn: () => apiGet<InviteInfo>(`/api/auth/invites/${encodeURIComponent(token ?? "")}`),
    enabled: Boolean(token),
    retry: false,
  });
}

export function useResetPassword() {
  return useMutation({
    meta: AUTH_FLOW,
    mutationFn: (data: ResetPasswordRequest) => apiSend<void>("POST", "/api/auth/password/reset", data),
  });
}

export function useChangePassword() {
  return useMutation({
    meta: AUTH_FLOW, // a wrong current password is 401 too
    mutationFn: (data: ChangePasswordRequest) => apiSend<void>("POST", "/api/auth/password/change", data),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiSend<void>("POST", "/api/auth/logout"),
    onSettled: async () => {
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== "auth" });
      await queryClient.invalidateQueries({ queryKey: ["auth"] });
    },
  });
}

/** "Start over" after the account exists: refresh the auth state, then the sign-in page. */
export function useRestartAtLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();
  return async () => {
    await queryClient.invalidateQueries({ queryKey: ["auth"] });
    router.push("/login");
  };
}
