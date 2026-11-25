"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import { RotateCwIcon } from "lucide-react";
import { useState } from "react";

import { NotAvailable } from "@/components/common/empty-state";
import { InlineError } from "@/components/common/notice";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { errorMessage, isNotImplemented } from "@/lib/api/client";

interface QueryStateProps<T> {
  query: UseQueryResult<T, Error>;
  children: (data: T) => React.ReactNode;
  /** Name used in the "not available yet" message for 501. */
  feature?: string;
  /** Rows of the default loading skeleton. */
  rows?: number;
  /** Placeholder in the shape of the content (`TableSkeleton`, `DetailPageSkeleton`); default `LoadingRows`. */
  loading?: React.ReactNode;
}

/**
 * Loading skeleton, error with retry, or the data. The skeleton shows at
 * once, so the page is complete from the first frame and the data fills it
 * in. Data that was already in the cache shows at once; data that had to
 * load fades in.
 */
export function QueryState<T>({ query, children, feature = "This screen", rows = 4, loading }: QueryStateProps<T>) {
  const [loadedLater] = useState(query.isPending);
  if (query.isPending) {
    return loading ? <div className="animate-skeleton-in">{loading}</div> : <LoadingRows rows={rows} />;
  }
  if (query.isError) {
    if (isNotImplemented(query.error)) return <NotAvailable what={feature} />;
    return (
      <div className="flex flex-col items-start gap-3">
        <InlineError message={errorMessage(query.error)} />
        <Button variant="outline" size="sm" onClick={() => query.refetch()}>
          <RotateCwIcon />
          Try again
        </Button>
      </div>
    );
  }
  if (!loadedLater) return <>{children(query.data)}</>;
  return <div className="animate-content-in">{children(query.data)}</div>;
}

/** Plain skeleton rows, for content that is not a table or a detail page. */
export function LoadingRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="animate-skeleton-in flex flex-col gap-2" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}
