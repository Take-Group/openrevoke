"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type { SlackAgentOut, SlackAppCreate, SlackTokensUpdate } from "@/lib/api/slack-types";

/** Polls while the connection is being opened, so "Connected" shows up without a reload. */
export function useSlackAgent() {
  return useQuery({
    queryKey: ["slack-agent"],
    queryFn: () => apiGet<SlackAgentOut>("/api/slack-agent"),
    refetchInterval: (query) => (query.state.data?.status === "connecting" ? 3000 : false),
  });
}

export function useCreateSlackApp() {
  return useApiMutation({
    mutationFn: (data: SlackAppCreate) => apiSend<SlackAgentOut>("POST", "/api/slack-agent/app", data),
    invalidate: ["slack-agent"],
    success: "Slack app created",
  });
}

export function useSaveSlackTokens() {
  return useApiMutation({
    mutationFn: (data: SlackTokensUpdate) => apiSend<SlackAgentOut>("PUT", "/api/slack-agent/tokens", data),
    invalidate: ["slack-agent"],
    success: "Token saved",
  });
}

export function useUpdateSlackAgent() {
  return useApiMutation({
    mutationFn: (enabled: boolean) => apiSend<SlackAgentOut>("PATCH", "/api/slack-agent", { enabled }),
    invalidate: ["slack-agent"],
  });
}

export function useRemoveSlackAgent() {
  return useApiMutation({
    mutationFn: () => apiSend<void>("DELETE", "/api/slack-agent"),
    invalidate: ["slack-agent"],
    success: "Slack app removed from Open Revoke",
  });
}

export function useSetSlackAvatar() {
  return useApiMutation({
    mutationFn: (file: File | null) => {
      const form = new FormData();
      if (file) form.append("file", file);
      return apiSend<SlackAgentOut>("POST", "/api/slack-agent/avatar", form);
    },
    invalidate: ["slack-agent"],
    success: "Icon set. Slack shows it within a few minutes",
  });
}
