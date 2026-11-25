import { DetailHeader } from "@/components/common/page-header";
import { StatStrip } from "@/components/common/stat";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Placeholders in the shape of the content they stand for, shown at once
 * while the data loads, so the page is there immediately and the data only
 * fills it in. Sizes match the real parts (`DataTable`, `DetailHeader`,
 * `StatStrip`), so nothing jumps when the data arrives.
 */

/** A `DataTable` card: header strip and rows with a leading avatar. */
export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div
      className="overflow-clip rounded-lg border border-frame bg-card shadow-card"
      aria-busy="true"
      aria-label="Loading"
    >
      <div className="flex h-9 items-center gap-6 border-b bg-subtle px-4">
        <Skeleton className="h-2.5 w-24" />
        <Skeleton className="h-2.5 w-16" />
        <Skeleton className="ml-auto h-2.5 w-12" />
      </div>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex h-11 items-center gap-3 border-b px-4 last:border-b-0">
          <Skeleton className="size-6 shrink-0 rounded-full" />
          {/* Varied widths read as text, a uniform bar reads as a loading bar. */}
          <Skeleton className="h-3" style={{ width: `${28 - ((i * 7) % 12)}%` }} />
          <Skeleton className="ml-auto h-3 w-16" />
          <Skeleton className="h-3 w-20 max-sm:hidden" />
        </div>
      ))}
    </div>
  );
}

interface DetailPageSkeletonProps {
  /** Facts in the strip under the header. */
  stats?: number;
  /** Tabs above the content; 0 for a page without tabs. */
  tabs?: number;
  rows?: number;
}

/** A detail page (person, app): header with avatar, stat strip, tabs and a table. */
export function DetailPageSkeleton({ stats = 4, tabs = 4, rows = 6 }: DetailPageSkeletonProps) {
  return (
    <div aria-busy="true" aria-label="Loading">
      <DetailHeader
        avatar={<Skeleton className="size-10 shrink-0 rounded-full" />}
        title={<Skeleton className="my-1 h-5 w-44" />}
        subtitle={<Skeleton className="mt-1.5 h-3 w-56" />}
        actions={
          <>
            <Skeleton className="h-9 w-28" />
            <Skeleton className="h-9 w-24" />
          </>
        }
      />
      <StatStrip>
        {Array.from({ length: stats }, (_, i) => (
          <div key={i} className="flex min-w-0 flex-1 flex-col gap-2 px-4 py-3">
            <Skeleton className="h-2.5 w-16" />
            <Skeleton className="h-3.5 w-12" />
          </div>
        ))}
      </StatStrip>
      {tabs > 0 && (
        <div className="mb-3 flex h-9 items-center gap-6 border-b">
          {Array.from({ length: tabs }, (_, i) => (
            <Skeleton key={i} className="h-3 w-16" />
          ))}
        </div>
      )}
      <TableSkeleton rows={rows} />
    </div>
  );
}
