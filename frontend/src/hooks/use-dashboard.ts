"use client";

import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api/client";
import type { Dashboard } from "@/lib/api/types";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiGet<Dashboard>("/api/dashboard"),
  });
}
