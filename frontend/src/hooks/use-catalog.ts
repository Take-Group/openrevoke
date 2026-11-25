"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api/client";
import type { CatalogAppList, CatalogAppOut } from "@/lib/api/catalog-types";
import { normalizeName } from "@/lib/brand-icons";

export type CatalogLookup = (...candidates: (string | null | undefined)[]) => CatalogAppOut | null;

/**
 * The app catalog (public, changes only with a deploy), as a lookup by catalog slug or app name.
 * Until it loads the lookup finds nothing and avatars show initials.
 */
export function useAppCatalog(): CatalogLookup {
  const { data } = useQuery({
    queryKey: ["catalog"],
    queryFn: () => apiGet<CatalogAppList>("/api/catalog/apps"),
    staleTime: Infinity,
    gcTime: Infinity,
  });
  return useMemo(() => {
    const bySlug = new Map<string, CatalogAppOut>();
    const byKey = new Map<string, CatalogAppOut>();
    for (const app of data?.items ?? []) {
      bySlug.set(app.slug, app);
      for (const key of app.keys) if (!byKey.has(key)) byKey.set(key, app);
    }
    return (...candidates) => {
      for (const candidate of candidates) {
        if (!candidate) continue;
        const found = bySlug.get(candidate) ?? byKey.get(normalizeName(candidate));
        if (found) return found;
      }
      return null;
    };
  }, [data]);
}
