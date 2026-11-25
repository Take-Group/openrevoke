"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type {
  AccountCreate,
  AccountKind,
  AccountOut,
  AccountStatus,
  AccountUpdate,
  Page,
} from "@/lib/api/types";

export interface AccountsParams {
  q?: string;
  status?: AccountStatus;
  kind?: AccountKind;
  unassigned?: boolean;
  limit?: number;
  offset?: number;
}

export function useAppAccounts(appId: string, params: AccountsParams = {}) {
  return useQuery({
    queryKey: ["accounts", appId, params],
    queryFn: () => apiGet<Page<AccountOut>>(`/api/apps/${appId}/accounts`, { ...params }),
    placeholderData: keepPreviousData,
  });
}

export function useCreateAccount(appId: string) {
  return useApiMutation({
    mutationFn: (data: AccountCreate) => apiSend<AccountOut>("POST", `/api/apps/${appId}/accounts`, data),
    invalidate: ["accounts", "app", "apps", "people", "person"],
    success: "Account added",
  });
}

export function useUpdateAccount() {
  return useApiMutation({
    mutationFn: ({ id, data }: { id: string; data: AccountUpdate }) =>
      apiSend<AccountOut>("PATCH", `/api/accounts/${id}`, data),
    invalidate: ["accounts", "app", "apps", "people", "person"],
    success: "Account saved",
  });
}
