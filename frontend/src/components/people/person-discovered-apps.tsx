"use client";

import { ScanSearchIcon } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { AppAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { TextLink } from "@/components/common/links";
import { QueryState } from "@/components/common/query-state";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import { SortHeader } from "@/components/data-table/column-header";
import { DataTable } from "@/components/data-table/data-table";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { usePersonDiscoveredApps } from "@/hooks/use-discovery";
import type { PersonDiscoveredApp } from "@/lib/api/discovery-types";

const columns: ColumnDef<PersonDiscoveredApp>[] = [
  {
    id: "name",
    accessorFn: (item) => item.catalog?.name ?? item.name,
    header: ({ column }) => <SortHeader column={column} title="App" />,
    cell: ({ row: { original: item } }) => (
      <div className="flex items-center gap-2.5">
        <AppAvatar name={item.catalog?.name ?? item.name} catalogSlug={item.catalog?.slug} size="sm" />
        <span className="font-medium">{item.catalog?.name ?? item.name}</span>
      </div>
    ),
  },
  {
    id: "open_revoke",
    header: "In Open Revoke",
    cell: ({ row: { original: item } }) => {
      if (!item.app) return <StatusBadge status="untracked" label="Not tracked" tone="warning" />;
      return (
        <TextLink href={`/apps/${item.app.id}`}>{item.has_account ? "Has an account" : "Tracked, no account seen"}</TextLink>
      );
    },
    meta: { className: "max-md:hidden w-52" },
  },
  {
    accessorKey: "email",
    header: "Signed in as",
    cell: ({ row }) => <span className="text-muted-foreground">{row.original.email}</span>,
    meta: { className: "max-md:hidden" },
  },
  {
    accessorKey: "last_seen_at",
    header: ({ column }) => <SortHeader column={column} title="Last sign-in" />,
    cell: ({ row }) => <RelativeTime value={row.original.last_seen_at} />,
    meta: { className: "w-32" },
  },
  {
    id: "token",
    header: "Token",
    cell: ({ row: { original: item } }) =>
      item.token_active === null ? (
        <span className="text-muted-foreground">Unknown</span>
      ) : item.token_active ? (
        "Live"
      ) : (
        <span className="text-muted-foreground">None</span>
      ),
    meta: { className: "max-md:hidden w-24" },
  },
];

/** Apps the person signed in to with Google. Useful before offboarding: untracked apps need a manual check. */
export function PersonDiscoveredApps({ personId }: { personId: string }) {
  const query = usePersonDiscoveredApps(personId);
  return (
    <QueryState query={query} loading={<TableSkeleton rows={4} />}>
      {(page) => (
        <DataTable
          columns={columns}
          data={page.items}
          getRowId={(item) => `${item.discovered_app_id}-${item.email}`}
          rowHref={(item) => `/discovery/${item.discovered_app_id}`}
          empty={
            <EmptyState
              icon={ScanSearchIcon}
              title="No sign-ins found"
              description={
                <>
                  Apps appear after a <TextLink href="/discovery">Google scan</TextLink>.
                </>
              }
            />
          }
        />
      )}
    </QueryState>
  );
}
