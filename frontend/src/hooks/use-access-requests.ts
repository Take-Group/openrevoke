"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend, buildQuery } from "@/lib/api/client";
import type {
  AccessRequestDecisionCreate,
  AccessRequestDetail,
  AccessRequestFilters,
  AccessRequestPage,
} from "@/lib/api/access-request-types";

/** Admins: requests with filters, newest first. */
export function useAccessRequests(params: AccessRequestFilters & { limit: number; offset: number }, enabled = true) {
  return useQuery({
    queryKey: ["access-requests", params],
    queryFn: () => apiGet<AccessRequestPage>("/api/access-requests", { ...params }),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** Admins: one request with its decisions and action. */
export function useAccessRequest(id: string) {
  return useQuery({
    queryKey: ["access-requests", "detail", id],
    queryFn: () => apiGet<AccessRequestDetail>(`/api/access-requests/${id}`),
  });
}

/** Admins: the admin step, or the manager's step decided for the manager (override). */
export function useDecideAccessRequest(id: string, decision: "approve" | "reject") {
  return useApiMutation({
    mutationFn: (data: AccessRequestDecisionCreate) =>
      apiSend<AccessRequestDetail>("POST", `/api/access-requests/${id}/${decision}`, data),
    invalidate: ["access-requests", "actions", "me"],
    success: decision === "approve" ? "Approved" : "Rejected",
  });
}

/** The CSV export URL for the same filters (a plain link; the browser sends the session cookie). */
export function accessRequestsExportUrl(filters: AccessRequestFilters): string {
  return `/api/access-requests/export${buildQuery({ ...filters })}`;
}
