"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type { AccessRequestDecisionCreate, AccessRequestDetail, AccessRequestStatus, MyApprovals } from "@/lib/api/access-request-types";
import type { MyAccess, MyAccessRequestCreate, MyAccessRequestResult, MyTeam } from "@/lib/api/me-types";

/** The signed-in user's accounts, requests and the apps they may ask for. */
export function useMyAccess() {
  return useQuery({ queryKey: ["me", "access"], queryFn: () => apiGet<MyAccess>("/api/me/access") });
}

/** Ask for an account in an app, for yourself or (person_id) a report; the app's policy decides who approves. */
export function useRequestAccess() {
  return useApiMutation({
    mutationFn: (data: MyAccessRequestCreate) => apiSend<MyAccessRequestResult>("POST", "/api/me/access-requests", data),
    invalidate: ["me"],
  });
}

/** The signed-in user's reports, their apps and what can be asked for them. */
export function useMyTeam() {
  return useQuery({ queryKey: ["me", "team"], queryFn: () => apiGet<MyTeam>("/api/me/team") });
}

/** Requests that wait (or waited) for the signed-in user as manager; `pending` drives the sidebar count. */
export function useMyApprovals(params: { status?: AccessRequestStatus[]; limit: number; offset: number }, enabled = true) {
  return useQuery({
    queryKey: ["me", "approvals", params],
    queryFn: () => apiGet<MyApprovals>("/api/me/approvals", params),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** One request the signed-in user decides or decided as manager (403 for anyone else's). */
export function useMyApproval(id: string) {
  return useQuery({
    queryKey: ["me", "approval", id],
    queryFn: () => apiGet<AccessRequestDetail>(`/api/me/approvals/${id}`),
  });
}

/** Approve or reject as the manager; a rejection needs a comment. */
export function useDecideMyApproval(id: string, decision: "approve" | "reject") {
  return useApiMutation({
    mutationFn: (data: AccessRequestDecisionCreate) =>
      apiSend<AccessRequestDetail>("POST", `/api/me/approvals/${id}/${decision}`, data),
    invalidate: ["me"],
    success: decision === "approve" ? "Approved" : "Rejected",
  });
}
