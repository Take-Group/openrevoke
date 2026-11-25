"use client";

import { useQuery } from "@tanstack/react-query";

import { useAuthState } from "@/hooks/use-auth";
import { apiGet } from "@/lib/api/client";
import type { SystemVersion } from "@/lib/api/system-types";

/** Version of this installation and the newest release (admins only: the API refuses a `user`). */
export function useSystemVersion() {
  const admin = useAuthState().data?.user?.role === "admin";
  return useQuery({
    queryKey: ["system", "version"],
    queryFn: () => apiGet<SystemVersion>("/api/system/version"),
    enabled: admin,
    // The worker checks hourly; the panel need not ask more often than every few minutes.
    staleTime: 5 * 60 * 1000,
  });
}
