"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type { AppBulkItem, AppBulkResult, AppPage } from "@/lib/api/inventory-types";
import type { AppCreate, AppDetail, AppUpdate, ConnectionStatus, Integration } from "@/lib/api/types";

export interface AppsParams {
  q?: string;
  /** Connection status. */
  status?: ConnectionStatus;
  integration?: Integration;
  category?: string;
  limit?: number;
  offset?: number;
}

export function useApps(params: AppsParams = {}) {
  return useQuery({
    queryKey: ["apps", params],
    queryFn: () => apiGet<AppPage>("/api/apps", { ...params }),
    placeholderData: keepPreviousData,
  });
}

export function useApp(id: string) {
  return useQuery({
    queryKey: ["app", id],
    queryFn: () => apiGet<AppDetail>(`/api/apps/${id}`),
  });
}

export function useCreateApp() {
  return useApiMutation({
    mutationFn: (data: AppCreate) => apiSend<AppDetail>("POST", "/api/apps", data),
    invalidate: ["apps"],
    success: (app) => `Added ${app.name}`,
  });
}

export function useUpdateApp(id: string) {
  return useApiMutation({
    mutationFn: (data: AppUpdate) => apiSend<AppDetail>("PATCH", `/api/apps/${id}`, data),
    invalidate: ["apps", "app", "accounts", "people", "person"],
    success: "App saved",
  });
}

export function useDeleteApp(id: string) {
  return useApiMutation({
    mutationFn: () => apiSend<void>("DELETE", `/api/apps/${id}`),
    invalidate: ["apps"],
    success: "App deleted",
  });
}

/** "Add several apps": catalog apps or names, created as manual and free; existing ones come back as skipped. */
export function useCreateApps() {
  return useApiMutation({
    mutationFn: (apps: AppBulkItem[]) => apiSend<AppBulkResult>("POST", "/api/apps/bulk", { apps }),
    invalidate: ["apps"],
    success: (result) =>
      `Added ${result.created.length} app${result.created.length === 1 ? "" : "s"}` +
      (result.skipped.length ? `, skipped ${result.skipped.length}` : ""),
  });
}

/** Uploads (`file`) or removes (`file: null`) an app's own logo. */
export function useAppLogo() {
  return useApiMutation({
    mutationFn: ({ id, file }: { id: string; file: File | null }) => {
      if (!file) return apiSend<void>("DELETE", `/api/apps/${id}/logo`);
      const form = new FormData();
      form.append("file", file);
      return apiSend<void>("PUT", `/api/apps/${id}/logo`, form);
    },
    invalidate: ["apps", "app", "people", "person", "me", "actions"],
    success: "Logo saved",
  });
}
