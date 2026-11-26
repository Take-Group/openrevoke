"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type {
  AccessProfileCreate,
  AccessProfileList,
  AccessProfileMemberList,
  AccessProfileOut,
  AccessProfileUpdate,
  AppRoleSuggestionList,
  MembersAssign,
  MembersAssignResult,
  PersonAccessDrift,
  PersonAccessProfileList,
  ProfileAssign,
  ProfileAssignResult,
  ProfileUnassignResult,
  SuggestedRemoval,
} from "@/lib/api/access-profile-types";
import type { ActionOut } from "@/lib/api/types";

// Every query lives under the "access-profiles" key, so one invalidation refreshes profiles, members and drift.

export function useAccessProfiles() {
  return useQuery({
    queryKey: ["access-profiles", "list"],
    queryFn: () => apiGet<AccessProfileList>("/api/access-profiles"),
  });
}

export function useAccessProfile(id: string) {
  return useQuery({
    queryKey: ["access-profiles", "detail", id],
    queryFn: () => apiGet<AccessProfileOut>(`/api/access-profiles/${id}`),
  });
}

export function useAccessProfileMembers(id: string) {
  return useQuery({
    queryKey: ["access-profiles", "members", id],
    queryFn: () => apiGet<AccessProfileMemberList>(`/api/access-profiles/${id}/members`),
  });
}

/** Roles of existing accounts per app, for the role field of the profile form. */
export function useAppRoleSuggestions() {
  return useQuery({
    queryKey: ["access-profiles", "app-roles"],
    queryFn: () => apiGet<AppRoleSuggestionList>("/api/access-profiles/app-roles"),
    select: (data) => new Map(data.items.map((item) => [item.app_id, item.roles])),
  });
}

export function usePersonAccessProfiles(personId: string) {
  return useQuery({
    queryKey: ["access-profiles", "person", personId],
    queryFn: () => apiGet<PersonAccessProfileList>(`/api/people/${personId}/access-profiles`),
  });
}

export function usePersonAccessDrift(personId: string) {
  return useQuery({
    queryKey: ["access-profiles", "drift", personId],
    queryFn: () => apiGet<PersonAccessDrift>(`/api/people/${personId}/access-drift`),
  });
}

export function useCreateAccessProfile() {
  return useApiMutation({
    mutationFn: (data: AccessProfileCreate) => apiSend<AccessProfileOut>("POST", "/api/access-profiles", data),
    invalidate: ["access-profiles"],
    success: (profile) => `Added ${profile.name}`,
  });
}

export function useUpdateAccessProfile(id: string) {
  return useApiMutation({
    mutationFn: (data: AccessProfileUpdate) => apiSend<AccessProfileOut>("PATCH", `/api/access-profiles/${id}`, data),
    invalidate: ["access-profiles"],
    success: "Profile saved",
  });
}

export function useDeleteAccessProfile(id: string) {
  return useApiMutation({
    mutationFn: () => apiSend<void>("DELETE", `/api/access-profiles/${id}`),
    invalidate: ["access-profiles", "person"],
    success: "Profile deleted",
  });
}

/** Preview (dry_run) or assignment; the caller toasts, since a preview is not a change. */
export function useAssignPersonProfiles(personId: string) {
  return useApiMutation({
    mutationFn: (body: ProfileAssign) =>
      apiSend<ProfileAssignResult>("POST", `/api/people/${personId}/access-profiles`, body),
    invalidate: ["access-profiles", "person", "people", "actions"],
  });
}

export function useAssignProfileMembers(profileId: string) {
  return useApiMutation({
    mutationFn: (body: MembersAssign) =>
      apiSend<MembersAssignResult>("POST", `/api/access-profiles/${profileId}/members`, body),
    invalidate: ["access-profiles", "person", "people", "actions"],
  });
}

export function useUnassignPersonProfile(personId: string) {
  return useApiMutation({
    mutationFn: (profileId: string) =>
      apiSend<ProfileUnassignResult>("DELETE", `/api/people/${personId}/access-profiles/${profileId}`),
    invalidate: ["access-profiles", "person"],
    success: (result) => `Removed ${result.profile.name}`,
  });
}

/** "Create removal actions" after unassigning: one delete_account action per suggested account. */
export function useCreateRemovals() {
  return useApiMutation({
    mutationFn: async (removals: SuggestedRemoval[]) => {
      const created: ActionOut[] = [];
      for (const removal of removals) {
        created.push(
          await apiSend<ActionOut>("POST", "/api/actions", {
            kind: "delete_account",
            app_id: removal.app.app_id,
            account_id: removal.account.account_id,
          }),
        );
      }
      return created;
    },
    invalidate: ["actions", "person", "access-profiles"],
    success: (created) => `${created.length} removal(s) wait for approval in Actions`,
  });
}
