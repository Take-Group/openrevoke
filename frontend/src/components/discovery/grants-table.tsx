"use client";

import type { DataColumn } from "@/components/data-table/features";

import { RecordLink } from "@/components/common/links";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge, type Tone } from "@/components/common/status-badge";
import { SortHeader } from "@/components/data-table/column-header";
import { DataTable } from "@/components/data-table/data-table";
import { formatWhen } from "@/lib/format";
import type { DirectoryStatus, DiscoveredGrantOut, GrantRisk } from "@/lib/api/discovery-types";

const DIRECTORY: Record<DirectoryStatus, { label: string; tone: Tone }> = {
  active: { label: "Active", tone: "success" },
  suspended: { label: "Suspended", tone: "warning" },
  deleted: { label: "Deleted", tone: "danger" },
  external: { label: "Outside the directory", tone: "neutral" },
};

const RISK: Record<GrantRisk, string> = {
  left: "Left the company",
  suspended: "Suspended in Google",
  deleted: "Deleted from Google",
};

const columns: DataColumn<DiscoveredGrantOut>[] = [
  {
    accessorKey: "email",
    header: ({ column }) => <SortHeader column={column} title="Person" />,
    cell: ({ row: { original: grant } }) => (
      <div className="min-w-0">
        {grant.person ? (
          <RecordLink href={`/people/${grant.person.id}`} className="font-medium">
            {grant.person.name}
          </RecordLink>
        ) : (
          <span className="font-medium">{grant.email}</span>
        )}
        {grant.person && <div className="truncate text-xs text-muted-foreground">{grant.email}</div>}
      </div>
    ),
  },
  {
    id: "risk",
    accessorFn: (grant) => (grant.risk ? 0 : 1),
    header: ({ column }) => <SortHeader column={column} title="Needs attention" />,
    cell: ({ row: { original: grant } }) =>
      grant.risk ? (
        <StatusBadge status={grant.risk} label={RISK[grant.risk]} tone="danger" />
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
    meta: { className: "w-48" },
  },
  {
    accessorKey: "directory_status",
    header: "Google",
    cell: ({ row: { original: grant } }) => {
      const state = DIRECTORY[grant.directory_status];
      const label = grant.deleted_at ? `${state.label} ${formatWhen(grant.deleted_at).split(",")[0]}` : state.label;
      return <StatusBadge status={grant.directory_status} label={label} tone={state.tone} />;
    },
    meta: { className: "max-md:hidden w-44" },
  },
  {
    accessorKey: "last_seen_at",
    header: ({ column }) => <SortHeader column={column} title="Last sign-in" />,
    cell: ({ row }) => <RelativeTime value={row.original.last_seen_at} />,
    meta: { className: "max-md:hidden w-32" },
  },
  {
    id: "token",
    accessorFn: (grant) => (grant.token_active === null ? -1 : Number(grant.token_active)),
    header: "Token",
    cell: ({ row: { original: grant } }) =>
      grant.token_active === null ? (
        <span className="text-muted-foreground">Unknown</span>
      ) : grant.token_active ? (
        "Live"
      ) : (
        <span className="text-muted-foreground">None</span>
      ),
    meta: { className: "max-md:hidden w-24" },
  },
];

export function GrantsTable({ grants }: { grants: DiscoveredGrantOut[] }) {
  return (
    <DataTable
      columns={columns}
      data={grants}
      getRowId={(grant) => grant.id}
      rowClassName={(grant) => (grant.risk ? "bg-destructive/[0.03]" : undefined)}
    />
  );
}
