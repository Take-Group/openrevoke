"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { useApiMutation, type ResourceKey } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type {
  ActionCreate,
  ActionList,
  ActionOut,
  ActionSecret,
  ActionStatus,
  BatchApproveResult,
} from "@/lib/api/types";

export interface ActionsParams {
  q?: string;
  status?: ActionStatus[];
  batch_id?: string;
  person_id?: string;
  app_id?: string;
  limit?: number;
  offset?: number;
}

const TOUCHED: ResourceKey[] = ["actions", "accounts", "app", "apps", "person", "people"];

/** A connector write between approval and its result: ExecuteActionWorkflow works on it. */
export function isMoving(action: ActionOut): boolean {
  if (action.status === "running" || action.status === "verifying") return true;
  return action.status === "approved" && action.kind !== "manual_task";
}

export function useActions(params: ActionsParams = {}, enabled = true) {
  return useQuery({
    queryKey: ["actions", params],
    queryFn: () => apiGet<ActionList>("/api/actions", { ...params }),
    placeholderData: keepPreviousData,
    enabled,
    // Approved writes run in the background: poll while some are moving.
    refetchInterval: (query) => (query.state.data?.items.some(isMoving) ? 2000 : false),
  });
}

export function useCreateAction() {
  return useApiMutation({
    mutationFn: (data: ActionCreate) => apiSend<ActionOut>("POST", "/api/actions", data),
    invalidate: TOUCHED,
    success: (action) =>
      action.kind === "manual_task"
        ? "Manual task created. It waits for approval in Actions."
        : "Action created. It waits for approval in Actions.",
  });
}

export type ActionTransition = "approve" | "cancel" | "complete" | "retry" | "by-hand";

const TRANSITION_TEXT: Record<ActionTransition, (action: ActionOut) => string> = {
  approve: (action) =>
    action.kind === "manual_task" ? "Approved. Do the task in the app, then mark it done." : "Approved. The write runs now.",
  cancel: () => "Action cancelled",
  complete: () => "Task marked as done",
  retry: () => "Retrying. The app is read first, so nothing is written twice.",
  "by-hand": () => "Now a manual task. Do it in the app, then mark it done.",
};

/** Approve and retry errors are shown inline by the caller (they may need a link to the connection settings). */
export function useActionTransition(transition: ActionTransition) {
  return useApiMutation({
    mutationFn: (id: string) => apiSend<ActionOut>("POST", `/api/actions/${id}/${transition}`),
    invalidate: TOUCHED,
    success: TRANSITION_TEXT[transition],
    toastErrors: transition !== "approve" && transition !== "retry",
  });
}

export function useApproveBatch() {
  return useApiMutation({
    mutationFn: (batchId: string) => apiSend<BatchApproveResult>("POST", `/api/actions/batch/${batchId}/approve`),
    invalidate: TOUCHED,
    success: (result) => {
      if (result.not_approved.length > 0) {
        const apps = [...new Set(result.not_approved.map((item) => item.action.app.name))].join(", ");
        toast.warning(
          `${result.not_approved.length} action(s) stay pending: writes are disabled for ${apps}. Turn on "Allow writes" in the app's connection settings, then approve them.`,
          { duration: 10000 },
        );
      }
      return `Approved ${result.items.length} action(s)`;
    },
  });
}

/**
 * Returns the one-time secret and deletes it on the server. It does not refresh the actions list:
 * the refreshed row loses `has_secret_result` and would unmount the dialog that shows the secret.
 * The dialog refreshes the list when it closes.
 */
export function useRevealSecret() {
  return useApiMutation({
    mutationFn: (id: string) => apiSend<ActionSecret>("POST", `/api/actions/${id}/reveal-secret`),
    invalidate: [],
  });
}
