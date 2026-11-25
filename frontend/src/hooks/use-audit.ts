"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api/client";
import type { AuditEventOut, Page } from "@/lib/api/types";

export interface AuditParams {
  q?: string;
  entity_type?: string;
  entity_id?: string;
  event?: string;
  app_id?: string;
  person_id?: string;
  limit?: number;
  offset?: number;
}

export function useAudit(params: AuditParams = {}) {
  return useQuery({
    queryKey: ["audit", params],
    queryFn: () => apiGet<Page<AuditEventOut>>("/api/audit", { ...params }),
    placeholderData: keepPreviousData,
  });
}
