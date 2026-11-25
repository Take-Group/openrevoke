"use client";

import { useRouter } from "next/navigation";
import { AppWindowIcon, HistoryIcon, RefreshCwIcon, SquareArrowOutUpRightIcon, UserSearchIcon } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { AppAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { Hint } from "@/components/common/info-tip";
import { INTEGRATION } from "@/components/common/integration-icon";
import { ConvertedMoney, ConvertedPrice } from "@/components/common/converted-money";
import { RelativeTime } from "@/components/common/relative-time";
import { ConnectionBadge, StatusDot, TONE_TEXT } from "@/components/common/status-badge";
import { SortHeader } from "@/components/data-table/column-header";
import { DataTable } from "@/components/data-table/data-table";
import { RowActions } from "@/components/data-table/row-actions";
import { DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { useSyncConnection } from "@/hooks/use-connection";
import { amountOf, humanize } from "@/lib/format";
import type { AppListItem, Integration } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/** Integration as quiet text with its icon, the hint in a tooltip. */
function IntegrationText({ integration }: { integration: Integration }) {
  const { icon: Icon, label, hint } = INTEGRATION[integration];
  return (
    <Hint label={hint}>
      <span className="inline-flex items-center gap-1.5 text-muted-foreground">
        <Icon className="size-3.5" />
        {label}
      </span>
    </Hint>
  );
}

function AppRowActions({ app }: { app: AppListItem }) {
  const router = useRouter();
  const sync = useSyncConnection(app.id);
  return (
    <RowActions>
      <DropdownMenuItem onClick={() => router.push(`/apps/${app.id}`)}>
        <SquareArrowOutUpRightIcon />
        Open
      </DropdownMenuItem>
      {app.connector_key && (
        <DropdownMenuItem disabled={sync.isPending} onClick={() => sync.mutate()}>
          <RefreshCwIcon />
          Sync now
        </DropdownMenuItem>
      )}
      {app.unassigned_count > 0 && (
        <DropdownMenuItem onClick={() => router.push(`/apps/${app.id}?accounts=unassigned`)}>
          <UserSearchIcon />
          Without owner
        </DropdownMenuItem>
      )}
      <DropdownMenuSeparator />
      <DropdownMenuItem onClick={() => router.push(`/audit?app=${app.id}`)}>
        <HistoryIcon />
        History
      </DropdownMenuItem>
    </RowActions>
  );
}

const columns: ColumnDef<AppListItem>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => <SortHeader column={column} title="App" />,
    cell: ({ row: { original: app } }) => (
      <div className="flex items-center gap-2.5">
        <AppAvatar name={app.name} slug={app.slug} connectorKey={app.connector_key} size="sm" />
        <span className="font-medium">{app.name}</span>
      </div>
    ),
  },
  {
    accessorKey: "integration",
    header: "Type",
    cell: ({ row }) => <IntegrationText integration={row.original.integration} />,
    meta: { className: "max-md:hidden w-28" },
  },
  {
    id: "connection",
    accessorFn: (app) => app.connection_status ?? "",
    header: ({ column }) => <SortHeader column={column} title="Connection" />,
    cell: ({ row: { original: app } }) =>
      app.integration === "manual" && !app.connection_status ? (
        <span className="text-muted-foreground">—</span>
      ) : (
        <ConnectionBadge status={app.connection_status} />
      ),
    meta: { className: "max-md:hidden w-36" },
  },
  {
    accessorKey: "active_seats",
    header: ({ column }) => <SortHeader column={column} title="Seats" />,
    cell: ({ row: { original: app } }) => (
      <span className="inline-flex items-center justify-end gap-2 tabular-nums">
        {app.unassigned_count > 0 && (
          <Hint label={`${app.unassigned_count} without owner`}>
            <span className={cn("inline-flex items-center gap-1 text-xs", TONE_TEXT.warning)}>
              <StatusDot tone="warning" />
              {app.unassigned_count}
            </span>
          </Hint>
        )}
        {app.active_seats}
      </span>
    ),
    meta: { align: "right", className: "max-md:hidden w-24" },
  },
  {
    id: "price",
    accessorFn: (app) => amountOf(app.price_converted ?? app.price),
    header: ({ column }) => <SortHeader column={column} title="Price" />,
    cell: ({ row: { original: app } }) =>
      app.pricing_model === "free" ? (
        <span className="text-muted-foreground">Free</span>
      ) : (
        <Hint label={humanize(app.pricing_model)}>
          <span>
            <ConvertedPrice converted={app.price_converted} original={app.price} className="text-muted-foreground" />
          </span>
        </Hint>
      ),
    meta: { align: "right", className: "max-md:hidden w-40" },
  },
  {
    id: "cost",
    accessorFn: (app) => amountOf(app.monthly_cost_converted ?? app.monthly_cost),
    header: ({ column }) => <SortHeader column={column} title="Monthly" />,
    cell: ({ row }) => (
      <ConvertedMoney converted={row.original.monthly_cost_converted} original={row.original.monthly_cost} className="items-end" />
    ),
    meta: { align: "right", className: "w-36" },
  },
  {
    accessorKey: "last_synced_at",
    header: ({ column }) => <SortHeader column={column} title="Synced" />,
    cell: ({ row }) => <RelativeTime value={row.original.last_synced_at} />,
    meta: { className: "max-md:hidden w-28" },
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => <AppRowActions app={row.original} />,
    meta: { align: "right", className: "w-px" },
  },
];

export function AppsTable({ apps, filtered, empty }: { apps: AppListItem[]; filtered: boolean; empty?: React.ReactNode }) {
  return (
    <DataTable
      columns={columns}
      data={apps}
      getRowId={(app) => app.id}
      rowHref={(app) => `/apps/${app.id}`}
      empty={filtered ? <EmptyState icon={AppWindowIcon} title="No matches" /> : empty}
    />
  );
}
