"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { apiGet, buildQuery } from "@/lib/api/client";
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

/** Export of the log with the same filters, oldest first (a plain link; the browser sends the session cookie). */
export function auditExportUrl(params: Omit<AuditParams, "limit" | "offset">, format: "csv" | "jsonl"): string {
  return `/api/audit/export${buildQuery({ ...params, format })}`;
}
