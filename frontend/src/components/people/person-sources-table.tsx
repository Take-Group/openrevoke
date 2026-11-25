"use client";

import { DatabaseIcon } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { EmptyState } from "@/components/common/empty-state";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge, TagBadge } from "@/components/common/status-badge";
import { DataTable } from "@/components/data-table/data-table";
import type { PersonLinkSource, PersonSourceOut } from "@/lib/api/types";

const SOURCE_LABEL: Record<PersonLinkSource, string> = { manual: "Manual", csv: "CSV", connection: "Connection" };

const columns: ColumnDef<PersonSourceOut>[] = [
  {
    accessorKey: "source_name",
    header: "Source",
    cell: ({ row: { original: source } }) => (
      <div className="leading-tight">
        <div className="font-medium">{source.source_name}</div>
        <div className="text-xs text-muted-foreground">{source.external_id}</div>
      </div>
    ),
  },
  {
    accessorKey: "source_type",
    header: "Type",
    cell: ({ row }) => <TagBadge>{SOURCE_LABEL[row.original.source_type]}</TagBadge>,
    meta: { className: "max-md:hidden" },
  },
  {
    accessorKey: "is_active",
    header: "In source",
    cell: ({ row }) => (
      <StatusBadge
        status={row.original.is_active ? "active" : "suspended"}
        label={row.original.is_active ? "Active" : "Inactive"}
      />
    ),
    meta: { className: "max-md:hidden" },
  },
  {
    accessorKey: "last_seen_at",
    header: "Last seen",
    cell: ({ row }) => <RelativeTime value={row.original.last_seen_at} />,
  },
];

export function PersonSourcesTable({ sources }: { sources: PersonSourceOut[] }) {
  return (
    <DataTable
      columns={columns}
      data={sources}
      getRowId={(source) => source.id}
      empty={<EmptyState icon={DatabaseIcon} title="No sources" />}
    />
  );
}
