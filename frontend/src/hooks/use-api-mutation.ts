"use client";

import { useMutation, useQueryClient, type MutationFunction } from "@tanstack/react-query";
import { toast } from "sonner";

import { errorMessage } from "@/lib/api/client";

/** Top-level query keys. Mutations invalidate whole resources by these. */
export type ResourceKey =
  | "dashboard"
  | "people"
  | "person"
  | "apps"
  | "app"
  | "accounts"
  | "connectors"
  | "sync-runs"
  | "actions"
  | "browser"
  | "audit"
  | "discovery"
  | "auth"
  | "users"
  | "invites"
  | "currencies"
  | "ai-settings"
  | "slack-agent"
  | "access-requests"
  | "onboarding"
  | "organization"
  | "me"
  | "api-tokens";

interface ApiMutationOptions<TData, TVariables> {
  mutationFn: MutationFunction<TData, TVariables>;
  /** Resources whose queries become stale after success. */
  invalidate: ResourceKey[];
  /** Toast text on success; a function gets the response. */
  success?: string | ((data: TData) => string);
  /** False when the caller shows the error itself (e.g. inline with a link). */
  toastErrors?: boolean;
}

/**
 * useMutation with the panel defaults: error toast with the API `detail`,
 * optional success toast, invalidation of the touched resources. Audit and
 * dashboard change with almost every write, so they are always refreshed.
 */
export function useApiMutation<TData, TVariables = void>({
  mutationFn,
  invalidate,
  success,
  toastErrors = true,
}: ApiMutationOptions<TData, TVariables>) {
  const queryClient = useQueryClient();
  return useMutation<TData, Error, TVariables>({
    mutationFn,
    onSuccess: async (data) => {
      const keys = new Set<ResourceKey>([...invalidate, "dashboard", "audit"]);
      await Promise.all([...keys].map((key) => queryClient.invalidateQueries({ queryKey: [key] })));
      if (success) toast.success(typeof success === "function" ? success(data) : success);
    },
    onError: (error) => {
      if (toastErrors) toast.error(errorMessage(error));
    },
  });
}
