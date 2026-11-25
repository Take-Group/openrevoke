"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type { AiModelList, AiModelsRequest, AiProvider, AiSettingsOut, AiSettingsUpdate, AiTestResult } from "@/lib/api/ai-types";

export function useAiSettings() {
  return useQuery({ queryKey: ["ai-settings"], queryFn: () => apiGet<AiSettingsOut>("/api/ai-settings") });
}

export function useSaveAiSettings() {
  return useApiMutation({
    mutationFn: (data: AiSettingsUpdate) => apiSend<AiSettingsOut>("PUT", "/api/ai-settings", data),
    invalidate: ["ai-settings", "slack-agent"],
    success: "AI model saved",
  });
}

/** "Connect": lists the models with a key that is not saved yet. Errors show in the form, not as a toast. */
export function useAiModels() {
  return useApiMutation({
    mutationFn: (data: AiModelsRequest) => apiSend<AiModelList>("POST", "/api/ai-settings/models", data),
    invalidate: [],
    toastErrors: false,
  });
}

/** Models of the saved connection (the API uses the saved key). */
export function useSavedAiModels(provider: AiProvider, baseUrl: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["ai-settings", "models", provider, baseUrl],
    queryFn: () => apiSend<AiModelList>("POST", "/api/ai-settings/models", { provider, base_url: baseUrl }),
    enabled,
    retry: false,
    staleTime: 5 * 60_000,
  });
}

export function useTestAi() {
  return useApiMutation({
    mutationFn: () => apiSend<AiTestResult>("POST", "/api/ai-settings/test"),
    invalidate: [],
  });
}
