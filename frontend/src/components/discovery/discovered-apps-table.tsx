"use client";

import { ScanSearchIcon } from "lucide-react";
import type { DataColumn } from "@/components/data-table/features";

import { AppAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { Hint } from "@/components/common/info-tip";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge, StatusDot, TONE_TEXT } from "@/components/common/status-badge";
import { SortHeader } from "@/components/data-table/column-header";
import { DataTable } from "@/components/data-table/data-table";
import { ReviewActions } from "@/components/discovery/review-actions";
import type { DiscoveredAppOut } from "@/lib/api/discovery-types";

const STATUS_LABEL = { new: "New", tracked: "Tracked", ignored: "Ignored" } as const;
const STATUS_TONE = { new: "info", tracked: "success", ignored: "neutral" } as const;

const columns: DataColumn<DiscoveredAppOut>[] = [
  {
    id: "name",
    // Sorts by the name people see: the catalog's full name when the app is known.
    accessorFn: (app) => app.catalog?.name ?? app.name,
    header: ({ column }) => <SortHeader column={column} title="App" />,
    cell: ({ row: { original: app } }) => {
      const name = app.catalog?.name ?? app.name;
      return (
        <div className="flex items-center gap-2.5">
          <AppAvatar name={name} catalogSlug={app.catalog?.slug} size="sm" />
          <div className="min-w-0">
            <div className="truncate font-medium">{name}</div>
            {app.app && app.app.name !== name && (
              <div className="truncate text-xs text-muted-foreground">Tracked as {app.app.name}</div>
            )}
          </div>
        </div>
      );
    },
    // Takes the free width and truncates long names, so the actions stay on a phone screen.
    meta: { className: "w-full max-w-0 min-w-28" },
  },
  {
    accessorKey: "users",
    header: ({ column }) => <SortHeader column={column} title="People" />,
    cell: ({ row }) => row.original.users,
    meta: { align: "right", className: "max-md:hidden w-24" },
  },
  {
    accessorKey: "users_at_risk",
    header: ({ column }) => <SortHeader column={column} title="Left or removed" />,
    cell: ({ row: { original: app } }) =>
      app.users_at_risk > 0 ? (
        <Hint label="People who left, are suspended or were deleted in Google, and signed in to this app">
          <span className={`inline-flex items-center gap-1.5 font-medium ${TONE_TEXT.danger}`}>
            <StatusDot tone="danger" />
            {app.users_at_risk}
          </span>
        </Hint>
      ) : (
        <span className="text-muted-foreground">0</span>
      ),
    meta: { align: "right", className: "max-md:hidden w-36" },
  },
  {
    id: "tokens",
    accessorFn: (app) => app.active_tokens ?? -1,
    header: ({ column }) => <SortHeader column={column} title="Live tokens" />,
    cell: ({ row: { original: app } }) =>
      app.active_tokens === null ? (
        <Hint label="The token inventory scope is not delegated">
          <span className="text-muted-foreground">—</span>
        </Hint>
      ) : (
        <span className="text-muted-foreground">{app.active_tokens}</span>
      ),
    meta: { align: "right", className: "max-md:hidden w-28" },
  },
  {
    accessorKey: "last_seen_at",
    header: ({ column }) => <SortHeader column={column} title="Last sign-in" />,
    cell: ({ row }) => <RelativeTime value={row.original.last_seen_at} />,
    meta: { className: "max-md:hidden w-32" },
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row: { original: app } }) => (
      <StatusBadge status={app.status} label={STATUS_LABEL[app.status]} tone={STATUS_TONE[app.status]} />
    ),
    meta: { className: "max-md:hidden w-28" },
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => <ReviewActions app={row.original} />,
    meta: { align: "right", className: "w-px whitespace-nowrap" },
  },
];

export function DiscoveredAppsTable({ apps, filtered }: { apps: DiscoveredAppOut[]; filtered: boolean }) {
  return (
    <DataTable
      columns={columns}
      data={apps}
      getRowId={(app) => app.id}
      rowHref={(app) => `/discovery/${app.id}`}
      empty={
        <EmptyState
          icon={ScanSearchIcon}
          title={filtered ? "No matches" : "No apps found yet"}
          description={filtered ? undefined : "Apps appear here after the first scan finishes."}
        />
      }
    />
  );
}
