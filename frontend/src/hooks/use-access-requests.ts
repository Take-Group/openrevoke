"use client";

import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api/client";
import type { AccessRequestPage, AccessRequestStatus } from "@/lib/api/access-request-types";

export function useAccessRequests(params: { status?: AccessRequestStatus; limit: number; offset: number }) {
  return useQuery({
    queryKey: ["access-requests", params],
    queryFn: () => apiGet<AccessRequestPage>("/api/access-requests", params),
  });
}
