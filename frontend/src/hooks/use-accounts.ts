"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend, buildQuery } from "@/lib/api/client";
import type { AccountImportResult } from "@/lib/api/inventory-types";
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

/** CSV of accounts for several apps; `dryRun` previews, `createApps` adds apps the file names but Open Revoke lacks. */
export function useImportAccounts() {
  return useApiMutation({
    mutationFn: ({ file, dryRun, createApps }: { file: File; dryRun: boolean; createApps: boolean }) => {
      const form = new FormData();
      form.append("file", file);
      const query = buildQuery({ dry_run: dryRun, create_apps: createApps });
      return apiSend<AccountImportResult>("POST", `/api/accounts/import${query}`, form);
    },
    invalidate: ["accounts", "app", "apps", "people", "person"],
  });
}

/** Pasted e-mails into one manual app; `dryRun` previews. */
export function usePasteAccounts(appId: string) {
  return useApiMutation({
    mutationFn: ({ emails, dryRun }: { emails: string; dryRun: boolean }) =>
      apiSend<AccountImportResult>("POST", `/api/apps/${appId}/accounts/bulk${buildQuery({ dry_run: dryRun })}`, {
        emails,
      }),
    invalidate: ["accounts", "app", "apps", "people", "person"],
  });
}
