"use client";

import { RefreshCwIcon } from "lucide-react";
import type { DataColumn } from "@/components/data-table/features";

import { EmptyState } from "@/components/common/empty-state";
import { Hint } from "@/components/common/info-tip";
import { QueryState } from "@/components/common/query-state";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import { DataTable } from "@/components/data-table/data-table";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { useSyncRuns } from "@/hooks/use-connection";
import type { AppDetail, SyncRunOut } from "@/lib/api/types";

function duration(run: SyncRunOut): string {
  if (!run.finished_at) return "—";
  const seconds = Math.max(0, Math.round((Date.parse(run.finished_at) - Date.parse(run.started_at)) / 1000));
  return seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
}

function Count({ value, sign }: { value: number; sign?: "+" | "−" }) {
  if (value === 0) return <span className="text-muted-foreground tabular-nums">0</span>;
  return (
    <span className="tabular-nums">
      {sign}
      {value}
    </span>
  );
}

const columns: DataColumn<SyncRunOut>[] = [
  { accessorKey: "started_at", header: "Started", cell: ({ row }) => <RelativeTime value={row.original.started_at} /> },
  { accessorKey: "status", header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status} /> },
  {
    id: "duration",
    header: "Duration",
    cell: ({ row }) => <span className="text-muted-foreground tabular-nums">{duration(row.original)}</span>,
    meta: { className: "max-md:hidden" },
  },
  {
    accessorKey: "accounts_seen",
    header: "Seen",
    cell: ({ row }) => <Count value={row.original.accounts_seen} />,
    meta: { align: "right", className: "max-md:hidden w-20" },
  },
  {
    accessorKey: "accounts_added",
    header: "Added",
    cell: ({ row }) => <Count value={row.original.accounts_added} sign="+" />,
    meta: { align: "right", className: "max-md:hidden w-20" },
  },
  {
    accessorKey: "accounts_removed",
    header: "Removed",
    cell: ({ row }) => <Count value={row.original.accounts_removed} sign="−" />,
    meta: { align: "right", className: "max-md:hidden w-24" },
  },
  {
    accessorKey: "error",
    header: "Error",
    cell: ({ row }) =>
      row.original.error ? (
        <Hint label={row.original.error}>
          <span className="block max-w-md truncate text-destructive">{row.original.error}</span>
        </Hint>
      ) : null,
    meta: { className: "w-full" },
  },
];

export function SyncRunsTab({ app }: { app: AppDetail }) {
  const query = useSyncRuns(app.id);
  return (
    <QueryState query={query} feature="Sync history" loading={<TableSkeleton rows={5} />}>
      {(page) => (
        <DataTable
          columns={columns}
          data={page.items}
          getRowId={(run) => run.id}
          empty={<EmptyState icon={RefreshCwIcon} title={app.connection ? "No syncs yet" : "Not connected"} />}
        />
      )}
    </QueryState>
  );
}
