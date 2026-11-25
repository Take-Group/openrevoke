"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type { MyAccess, MyAccessRequestCreate, MyAccessRequestResult } from "@/lib/api/me-types";

/** The signed-in user's accounts, requests and the apps they may ask for. */
export function useMyAccess() {
  return useQuery({ queryKey: ["me", "access"], queryFn: () => apiGet<MyAccess>("/api/me/access") });
}

/** Ask for an account in an app; the app's self-service policy decides if an admin approves it. */
export function useRequestAccess() {
  return useApiMutation({
    mutationFn: (data: MyAccessRequestCreate) => apiSend<MyAccessRequestResult>("POST", "/api/me/access-requests", data),
    invalidate: ["me"],
  });
}
