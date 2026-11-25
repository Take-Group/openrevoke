"use client";

import { QueryState } from "@/components/common/query-state";
import { usePerson } from "@/hooks/use-people";
import type { PersonDetail } from "@/lib/api/types";

/** Loads one person for a page under `/people/<id>/...` and renders it once loaded. */
export function PersonQuery({ id, children }: { id: string; children: (person: PersonDetail) => React.ReactNode }) {
  const query = usePerson(id);
  return (
    <QueryState query={query} rows={6}>
      {children}
    </QueryState>
  );
}
