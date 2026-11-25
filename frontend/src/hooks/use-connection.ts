"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type {
  ConnectionCheckResult,
  ConnectionOut,
  ConnectionUpsert,
  Page,
  SyncRunOut,
} from "@/lib/api/types";

export function useSaveConnection(appId: string) {
  return useApiMutation({
    mutationFn: (data: ConnectionUpsert) => apiSend<ConnectionOut>("PUT", `/api/apps/${appId}/connection`, data),
    invalidate: ["app", "apps", "sync-runs"],
    success: "Connection saved",
  });
}

export function useCheckConnection(appId: string) {
  return useApiMutation({
    mutationFn: () => apiSend<ConnectionCheckResult>("POST", `/api/apps/${appId}/connection/check`),
    invalidate: ["app", "apps"],
  });
}

export function useSyncConnection(appId: string) {
  return useApiMutation({
    mutationFn: () => apiSend<SyncRunOut>("POST", `/api/apps/${appId}/connection/sync`),
    invalidate: ["app", "apps", "sync-runs", "accounts", "people", "person"],
    success: "Sync started",
  });
}

export function useSyncRuns(appId: string) {
  return useQuery({
    queryKey: ["sync-runs", appId],
    queryFn: () => apiGet<Page<SyncRunOut>>(`/api/apps/${appId}/sync-runs`, { limit: 50 }),
    // A running sync finishes in the background: poll until it does.
    refetchInterval: (query) =>
      query.state.data?.items.some((run) => run.status === "running") ? 3000 : false,
  });
}

/**
 * True while a sync of the app runs. When it finishes, the app, its accounts
 * and everything that counts them are refetched.
 */
export function useSyncInProgress(appId: string): boolean {
  const queryClient = useQueryClient();
  const runs = useSyncRuns(appId);
  const running = runs.data?.items.some((run) => run.status === "running") ?? false;
  const wasRunning = useRef(running);

  useEffect(() => {
    if (wasRunning.current && !running) {
      for (const key of ["app", "apps", "accounts", "people", "person", "dashboard", "audit"]) {
        void queryClient.invalidateQueries({ queryKey: [key] });
      }
    }
    wasRunning.current = running;
  }, [running, queryClient]);

  return running;
}
