"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type {
  InviteCreate,
  InviteCreated,
  InviteList,
  OrganizationSettingsOut,
  OrganizationUpdate,
  ResetLinkOut,
  UserOut,
  UserRole,
} from "@/lib/api/auth-types";

export function useUsers() {
  return useQuery({ queryKey: ["users"], queryFn: () => apiGet<UserOut[]>("/api/users") });
}

export function useInvites(enabled = true) {
  return useQuery({ queryKey: ["invites"], queryFn: () => apiGet<InviteList>("/api/invites"), enabled });
}

export function useCreateInvite() {
  return useApiMutation({
    mutationFn: (data: InviteCreate) => apiSend<InviteCreated>("POST", "/api/invites", data),
    invalidate: ["invites"],
  });
}

export function useRevokeInvite() {
  return useApiMutation({
    mutationFn: (inviteId: string) => apiSend<void>("DELETE", `/api/invites/${inviteId}`),
    invalidate: ["invites"],
    success: "Invite revoked",
  });
}

export function useUpdateUserRole() {
  return useApiMutation({
    mutationFn: ({ userId, role }: { userId: string; role: UserRole }) =>
      apiSend<UserOut>("PATCH", `/api/users/${userId}`, { role }),
    invalidate: ["users", "auth"],
    success: "Role changed",
  });
}

/** Let a sign-up in (nothing is sent: tell them yourself). Reject with `useRemoveUser`. */
export function useApproveUser() {
  return useApiMutation({
    mutationFn: (userId: string) => apiSend<UserOut>("POST", `/api/users/${userId}/approve`),
    invalidate: ["users"],
    success: (user) => `${user.name} can sign in now. Let them know`,
  });
}

/** A one-time password reset link (24 hours) for the admin to pass on; no e-mail. */
export function useCreateResetLink() {
  return useApiMutation({
    mutationFn: (userId: string) => apiSend<ResetLinkOut>("POST", `/api/users/${userId}/reset-link`),
    invalidate: [],
  });
}

export function useResetUserTotp() {
  return useApiMutation({
    mutationFn: (userId: string) => apiSend<UserOut>("POST", `/api/users/${userId}/reset-totp`),
    invalidate: ["users", "auth"],
    success: "2FA reset: the user sets up a new authenticator at the next sign-in",
  });
}

export function useRemoveUser() {
  return useApiMutation({
    mutationFn: (userId: string) => apiSend<void>("DELETE", `/api/users/${userId}`),
    invalidate: ["users"],
    success: "User removed",
  });
}

/** The organization with its sign-up rules (admins only). */
export function useOrganizationSettings() {
  return useQuery({
    queryKey: ["organization"],
    queryFn: () => apiGet<OrganizationSettingsOut>("/api/organization"),
  });
}

export function useUpdateOrganization(success = "Organization saved") {
  return useApiMutation({
    mutationFn: (data: OrganizationUpdate) => apiSend<OrganizationSettingsOut>("PATCH", "/api/organization", data),
    // A new currency changes every converted amount.
    invalidate: ["organization", "auth", "apps", "app", "people", "person", "accounts"],
    success,
  });
}
