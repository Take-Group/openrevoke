"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend, buildQuery } from "@/lib/api/client";
import type {
  ImportResult,
  OffboardResult,
  OnboardRequest,
  OnboardResult,
  PersonCreate,
  PersonDetail,
  PersonKind,
  PersonPage,
  PersonStatus,
  PersonUpdate,
} from "@/lib/api/types";

export interface PeopleParams {
  q?: string;
  status?: PersonStatus;
  kind?: PersonKind;
  /** Only people with no manager set. */
  no_manager?: boolean;
  limit?: number;
  offset?: number;
}

export function usePeople(params: PeopleParams = {}, enabled = true) {
  return useQuery({
    queryKey: ["people", params],
    queryFn: () => apiGet<PersonPage>("/api/people", { ...params }),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function usePerson(id: string) {
  return useQuery({
    queryKey: ["person", id],
    queryFn: () => apiGet<PersonDetail>(`/api/people/${id}`),
  });
}

export function useCreatePerson() {
  return useApiMutation({
    mutationFn: (data: PersonCreate) => apiSend<PersonDetail>("POST", "/api/people", data),
    invalidate: ["people"],
    success: (person) => `Added ${person.first_name} ${person.last_name}`,
  });
}

export function useUpdatePerson(id: string) {
  return useApiMutation({
    mutationFn: (data: PersonUpdate) => apiSend<PersonDetail>("PATCH", `/api/people/${id}`, data),
    invalidate: ["people", "person", "accounts"],
    success: "Person saved",
  });
}

/** Person or service account, set by hand: syncs keep it. */
export function useSetPersonKind(id: string) {
  return useApiMutation({
    mutationFn: (kind: PersonKind) => apiSend<PersonDetail>("PATCH", `/api/people/${id}`, { kind }),
    invalidate: ["people", "person"],
    success: (person) => (person.kind === "service" ? "Marked as service account" : "Marked as person"),
  });
}

export function useImportPeople() {
  return useApiMutation({
    mutationFn: ({ file, dryRun }: { file: File; dryRun: boolean }) => {
      const form = new FormData();
      form.append("file", file);
      return apiSend<ImportResult>("POST", `/api/people/import${buildQuery({ dry_run: dryRun })}`, form);
    },
    invalidate: ["people", "person"],
  });
}

export function useOffboardPerson(id: string) {
  return useApiMutation({
    mutationFn: () => apiSend<OffboardResult>("POST", `/api/people/${id}/offboard`),
    invalidate: ["people", "person", "actions", "accounts", "apps"],
    success: (result) => `Offboarding started: ${result.actions.length} action(s) wait for approval`,
  });
}

export function useOnboardPerson(id: string) {
  return useApiMutation({
    mutationFn: (body: OnboardRequest) => apiSend<OnboardResult>("POST", `/api/people/${id}/onboard`, body),
    invalidate: ["people", "person", "actions", "accounts", "apps"],
    success: (result) => `Onboarding started: ${result.actions.length} action(s) wait for approval`,
  });
}

/** Only a person without accounts and actions (PersonDetail.can_delete); 409 otherwise. */
export function useDeletePerson(id: string) {
  return useApiMutation({
    mutationFn: () => apiSend<void>("DELETE", `/api/people/${id}`),
    invalidate: ["people"],
    success: "Person deleted",
  });
}
