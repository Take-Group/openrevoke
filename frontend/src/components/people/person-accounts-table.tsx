"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRoundIcon, SquareArrowOutUpRightIcon, UserMinusIcon } from "lucide-react";
import type { DataColumn } from "@/components/data-table/features";

import { AppAvatar } from "@/components/common/avatars";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { EmptyState } from "@/components/common/empty-state";
import { ConvertedMoney } from "@/components/common/converted-money";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge, TagBadge } from "@/components/common/status-badge";
import { WriteModeLine } from "@/components/common/write-mode-badge";
import { SortHeader } from "@/components/data-table/column-header";
import { DataTable } from "@/components/data-table/data-table";
import { RowActions } from "@/components/data-table/row-actions";
import { DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { useCreateAction } from "@/hooks/use-actions";
import { useApps } from "@/hooks/use-apps";
import { accountLabel, amountOf, humanize } from "@/lib/format";
import { removeVerb } from "@/lib/write-mode";
import type { AppListItem, PersonAccountOut, PersonDetail } from "@/lib/api/types";

function columns(
  appOf: (account: PersonAccountOut) => AppListItem | undefined,
  onRemove: (account: PersonAccountOut) => void,
): DataColumn<PersonAccountOut>[] {
  return [
    {
      id: "app",
      accessorFn: (account) => account.app.name,
      header: ({ column }) => <SortHeader column={column} title="App" />,
      cell: ({ row: { original: account } }) => (
        <div className="flex items-center gap-2.5">
          <AppAvatar
            name={account.app.name}
            slug={account.app.slug}
            logoUrl={account.app.logo_url}
            connectorKey={appOf(account)?.connector_key}
            size="sm"
          />
          <span className="font-medium">{account.app.name}</span>
        </div>
      ),
    },
    {
      id: "account",
      accessorFn: (account) => accountLabel(account),
      header: ({ column }) => <SortHeader column={column} title="Account" />,
      cell: ({ row: { original: account } }) => (
        <span className="flex items-center gap-2">
          <span className="truncate">{accountLabel(account)}</span>
          {account.kind !== "person" && <TagBadge>{humanize(account.kind)}</TagBadge>}
        </span>
      ),
      meta: { className: "max-md:hidden" },
    },
    {
      accessorKey: "role",
      header: ({ column }) => <SortHeader column={column} title="Role" />,
      cell: ({ getValue }) => <span className="text-muted-foreground">{(getValue() as string | null) ?? "—"}</span>,
      meta: { className: "max-md:hidden" },
    },
    {
      accessorKey: "status",
      header: ({ column }) => <SortHeader column={column} title="Status" />,
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: "match_method",
      header: "Matched by",
      cell: ({ getValue }) => <span className="text-muted-foreground">{humanize(getValue() as string)}</span>,
      meta: { className: "max-md:hidden" },
    },
    {
      accessorKey: "last_seen_at",
      header: ({ column }) => <SortHeader column={column} title="Last seen" />,
      cell: ({ row }) => <RelativeTime value={row.original.last_seen_at} />,
      meta: { className: "max-md:hidden" },
    },
    {
      id: "cost",
      accessorFn: (account) => amountOf(account.monthly_cost_converted ?? account.monthly_cost),
      header: ({ column }) => <SortHeader column={column} title="Monthly" />,
      cell: ({ row }) => (
        <ConvertedMoney converted={row.original.monthly_cost_converted} original={row.original.monthly_cost} className="items-end" />
      ),
      meta: { align: "right", className: "max-md:hidden" },
    },
    {
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: ({ row: { original: account } }) => <AccountMenu account={account} app={appOf(account)} onRemove={onRemove} />,
      meta: { align: "right", className: "w-px" },
    },
  ];
}

function AccountMenu({
  account,
  app,
  onRemove,
}: {
  account: PersonAccountOut;
  app: AppListItem | undefined;
  onRemove: (account: PersonAccountOut) => void;
}) {
  const router = useRouter();
  return (
    <RowActions>
      <DropdownMenuItem onClick={() => router.push(`/apps/${account.app.app_id}`)}>
        <SquareArrowOutUpRightIcon />
        Open app
      </DropdownMenuItem>
      {account.status !== "removed" && (
        <>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onClick={() => onRemove(account)}>
            <UserMinusIcon />
            {removeVerb(app)} from app
          </DropdownMenuItem>
        </>
      )}
    </RowActions>
  );
}

export function PersonAccountsTable({ person }: { person: PersonDetail }) {
  const [removing, setRemoving] = useState<PersonAccountOut | null>(null);
  const createAction = useCreateAction();
  const apps = useApps({ limit: 500 });
  const appOf = (account: PersonAccountOut) => apps.data?.items.find((app) => app.id === account.app.app_id);
  const removingApp = removing ? appOf(removing) : undefined;
  const verb = removeVerb(removingApp);

  const confirmRemove = () => {
    if (!removing) return;
    createAction.mutate(
      { kind: "delete_account", app_id: removing.app.app_id, account_id: removing.id, person_id: person.id },
      { onSuccess: () => setRemoving(null) },
    );
  };

  return (
    <>
      <DataTable
        columns={columns(appOf, setRemoving)}
        data={person.accounts}
        getRowId={(account) => account.id}
        rowHref={(account) => `/apps/${account.app.app_id}`}
        rowClassName={(account) => (account.status === "removed" ? "opacity-55" : undefined)}
        empty={<EmptyState icon={KeyRoundIcon} title="No accounts" />}
      />
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(open) => !open && setRemoving(null)}
        title={`${verb} from ${removing?.app.name ?? "app"}?`}
        description={removing ? accountLabel(removing) : undefined}
        confirmLabel="Create action"
        destructive
        pending={createAction.isPending}
        onConfirm={confirmRemove}
      >
        {removingApp && (
          <WriteModeLine mode={removingApp.delete_mode} what={verb === "Suspend" ? "suspend" : "remove"} />
        )}
      </ConfirmDialog>
    </>
  );
}
