"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { ApiError, apiGet, apiSend } from "@/lib/api/client";
import type { BrowserOpenRequest, BrowserState, BrowserTab } from "@/lib/api/types";

export function useBrowserState() {
  return useQuery({
    queryKey: ["browser"],
    queryFn: () => apiGet<BrowserState>("/api/browser"),
    // 4xx and 501 ("later stage") do not get better with a retry.
    retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status <= 501) && count < 2,
    refetchInterval: (query) => (query.state.error ? false : 15000),
  });
}

export function useOpenInBrowser() {
  return useApiMutation({
    mutationFn: (data: BrowserOpenRequest) => apiSend<BrowserTab>("POST", "/api/browser/open", data),
    invalidate: ["browser", "apps"],
    success: (tab) => `Opened ${tab.title || tab.url}. Log in in the live view.`,
  });
}
