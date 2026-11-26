"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type {
  DiscoveredAppDetail,
  DiscoveredAppOut,
  DiscoveredAppStatus,
  DiscoveredAppUpdate,
  DiscoveryOverview,
  DiscoverySourceCreate,
  GoogleCloudSetupOut,
  GoogleCloudSetupStart,
  GoogleOAuthStart,
  GoogleOAuthStartOut,
  PersonDiscoveredApp,
  ScanRunOut,
} from "@/lib/api/discovery-types";
import type { Page } from "@/lib/api/types";

/** Overview of app discovery. Polls while a scan runs and refreshes the found apps when it ends. */
export function useDiscovery() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["discovery", "overview"],
    queryFn: () => apiGet<DiscoveryOverview>("/api/discovery"),
    refetchInterval: (state) => (state.state.data?.scan_running ? 3000 : false),
  });
  const running = query.data?.scan_running ?? false;
  const wasRunning = useRef(running);
  useEffect(() => {
    if (wasRunning.current && !running) {
      for (const key of ["discovery", "dashboard", "people", "person", "apps", "audit"]) {
        void queryClient.invalidateQueries({ queryKey: [key] });
      }
    }
    wasRunning.current = running;
  }, [running, queryClient]);
  return query;
}

export interface DiscoveredAppsParams {
  q?: string;
  status?: DiscoveredAppStatus;
  at_risk?: boolean;
  limit?: number;
  offset?: number;
}

export function useDiscoveredApps(params: DiscoveredAppsParams) {
  return useQuery({
    queryKey: ["discovery", "apps", params],
    queryFn: () => apiGet<Page<DiscoveredAppOut>>("/api/discovery/apps", { ...params, at_risk: params.at_risk || undefined }),
  });
}

export function useDiscoveredApp(id: string) {
  return useQuery({
    queryKey: ["discovery", "app", id],
    queryFn: () => apiGet<DiscoveredAppDetail>(`/api/discovery/apps/${id}`),
  });
}

export function usePersonDiscoveredApps(personId: string) {
  return useQuery({
    queryKey: ["discovery", "person", personId],
    queryFn: () => apiGet<Page<PersonDiscoveredApp>>(`/api/people/${personId}/discovered-apps`),
  });
}

export function useScanNow() {
  return useApiMutation({
    mutationFn: () => apiSend<ScanRunOut>("POST", "/api/discovery/scan"),
    invalidate: ["discovery"],
    success: "Scan started",
  });
}

export function useConnectDiscoverySource() {
  return useApiMutation({
    mutationFn: (data: DiscoverySourceCreate) => apiSend<DiscoveryOverview>("POST", "/api/discovery/source", data),
    invalidate: ["discovery", "apps", "people"],
    success: "Google Workspace connected. The first scan is running",
    toastErrors: false,
  });
}

/** Connect with Google: the API returns Google's consent screen, the tab goes there. */
export function useStartGoogleOAuth() {
  return useApiMutation({
    mutationFn: async (data: GoogleOAuthStart) => {
      const out = await apiSend<GoogleOAuthStartOut>("POST", "/api/discovery/google-oauth/start", data);
      window.location.assign(out.authorization_url);
      return out;
    },
    invalidate: [],
    toastErrors: false,
  });
}

const SETUP_ACTIVE = new Set(["running", "waiting_for_consent"]);

/** Automatic Google Cloud setup. Polls while it runs; refreshes Discovery when it connects. */
export function useGoogleCloudSetup() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["discovery", "google-cloud-setup"],
    queryFn: () => apiGet<GoogleCloudSetupOut>("/api/discovery/google-cloud-setup"),
    refetchInterval: (state) => (SETUP_ACTIVE.has(state.state.data?.status ?? "") ? 2000 : false),
  });
  const status = query.data?.status;
  useEffect(() => {
    if (status === "connected") {
      for (const key of ["discovery", "dashboard", "people", "apps"]) {
        void queryClient.invalidateQueries({ queryKey: [key] });
      }
    }
  }, [status, queryClient]);
  return query;
}

export function useStartGoogleCloudSetup() {
  return useApiMutation({
    mutationFn: (data: GoogleCloudSetupStart) =>
      apiSend<GoogleCloudSetupOut>("POST", "/api/discovery/google-cloud-setup", data),
    invalidate: ["discovery"],
  });
}

/**
 * Result of the Google callback, passed back in the URL (`google=connected` or `google_error`).
 * Shows the success toast once and removes the parameters; returns the error to show inline.
 */
export function useGoogleOAuthResult() {
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const failed = params.get("google_error");
    const connected = params.get("google") === "connected";
    if (!failed && !connected) return;
    if (connected) toast.success("Google Workspace connected. People are importing and the first scan is running");
    // eslint-disable-next-line react-hooks/set-state-in-effect -- read once from the URL after Google's redirect
    if (failed) setError(failed);
    params.delete("google");
    params.delete("google_error");
    const rest = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${rest ? `?${rest}` : ""}`);
  }, []);
  return error;
}

export function useUpdateDiscoveredApp(id: string) {
  return useApiMutation({
    mutationFn: (data: DiscoveredAppUpdate) =>
      apiSend<DiscoveredAppDetail>("PATCH", `/api/discovery/apps/${id}`, data),
    invalidate: ["discovery"],
  });
}

export function useTrackDiscoveredApp(id: string) {
  return useApiMutation({
    mutationFn: (options: { create_accounts?: boolean } | void) =>
      apiSend<DiscoveredAppDetail>("POST", `/api/discovery/apps/${id}/track`, options ?? undefined),
    invalidate: ["discovery", "apps", "accounts", "people", "person"],
    success: (app) =>
      `Tracking ${app.app?.name ?? app.name}` +
      (app.accounts_created != null ? `, ${app.accounts_created} account(s) added` : ""),
  });
}
