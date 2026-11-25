"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type { ApiTokenCreate, ApiTokenCreated, ApiTokenList } from "@/lib/api/api-token-types";

/** The signed-in user's API tokens and the MCP server address. */
export function useApiTokens() {
  return useQuery({ queryKey: ["api-tokens"], queryFn: () => apiGet<ApiTokenList>("/api/api-tokens") });
}

/** The response carries the token itself, shown once. */
export function useCreateApiToken() {
  return useApiMutation({
    mutationFn: (data: ApiTokenCreate) => apiSend<ApiTokenCreated>("POST", "/api/api-tokens", data),
    invalidate: ["api-tokens"],
  });
}

export function useRevokeApiToken() {
  return useApiMutation({
    mutationFn: (tokenId: string) => apiSend<void>("DELETE", `/api/api-tokens/${tokenId}`),
    invalidate: ["api-tokens"],
    success: "Token revoked",
  });
}
