"use client";

import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api/client";
import type { ConnectorOut, Page } from "@/lib/api/types";

export function useConnectors() {
  return useQuery({
    queryKey: ["connectors"],
    queryFn: () => apiGet<Page<ConnectorOut>>("/api/connectors"),
    staleTime: 5 * 60 * 1000,
  });
}
