"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type {
  AppCreate,
  AppDetail,
  AppListItem,
  AppUpdate,
  ConnectionStatus,
  Integration,
  Page,
} from "@/lib/api/types";

export interface AppsParams {
  q?: string;
  /** Connection status. */
  status?: ConnectionStatus;
  integration?: Integration;
  limit?: number;
  offset?: number;
}

export function useApps(params: AppsParams = {}) {
  return useQuery({
    queryKey: ["apps", params],
    queryFn: () => apiGet<Page<AppListItem>>("/api/apps", { ...params }),
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
