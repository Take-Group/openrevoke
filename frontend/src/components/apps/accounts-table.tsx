"use client";

import { useRouter } from "next/navigation";
import { KeyRoundIcon, SquareArrowOutUpRightIcon } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { EmptyState } from "@/components/common/empty-state";
import { ConvertedMoney } from "@/components/common/converted-money";
import { PersonPicker } from "@/components/common/person-picker";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge, TagBadge } from "@/components/common/status-badge";
import { SortHeader } from "@/components/data-table/column-header";
import { DataTable } from "@/components/data-table/data-table";
import { RowActions } from "@/components/data-table/row-actions";
import {
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { useUpdateAccount } from "@/hooks/use-accounts";
import { accountLabel, amountOf, humanize } from "@/lib/format";
import type { AccountKind, AccountOut } from "@/lib/api/types";

const KINDS: { value: AccountKind; label: string }[] = [
  { value: "person", label: "Person" },
  { value: "service", label: "Service account" },
  { value: "unknown", label: "Unknown" },
];

function AccountIdentity({ account }: { account: AccountOut }) {
  const main = accountLabel(account);
  const extra = [account.display_name, account.username].filter((value) => value && value !== main);
  return (
    <div className="min-w-0 leading-tight">
      <div className="truncate font-medium">{main}</div>
      {extra.length > 0 && <div className="truncate text-xs text-muted-foreground">{extra.join(" · ")}</div>}
    </div>
  );
}

function Owner({ account }: { account: AccountOut }) {
  const update = useUpdateAccount();
  return (
    <PersonPicker
      value={account.person}
      allowClear
      disabled={update.isPending}
      placeholder={account.kind === "service" ? "Service" : "Assign"}
      onChange={(person) => update.mutate({ id: account.id, data: { person_id: person?.id ?? null } })}
    />
  );
}

function AccountMenu({ account }: { account: AccountOut }) {
  const router = useRouter();
  const update = useUpdateAccount();
  return (
    <RowActions>
      <DropdownMenuGroup>
        <DropdownMenuLabel>Kind</DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={account.kind}
          onValueChange={(kind) => update.mutate({ id: account.id, data: { kind: kind as AccountKind } })}
        >
          {KINDS.map((kind) => (
            <DropdownMenuRadioItem key={kind.value} value={kind.value} disabled={update.isPending}>
              {kind.label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuGroup>
      {account.person && (
        <>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => router.push(`/people/${account.person!.person_id}`)}>
            <SquareArrowOutUpRightIcon />
            Open owner
          </DropdownMenuItem>
        </>
      )}
    </RowActions>
  );
}

const columns: ColumnDef<AccountOut>[] = [
  {
    id: "account",
    accessorFn: (account) => accountLabel(account),
    header: ({ column }) => <SortHeader column={column} title="Account" />,
    cell: ({ row }) => <AccountIdentity account={row.original} />,
    meta: { className: "w-full max-w-0 min-w-44" },
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
    id: "owner",
    accessorFn: (account) => (account.person ? `${account.person.first_name} ${account.person.last_name}` : ""),
    header: ({ column }) => <SortHeader column={column} title="Owner" />,
    cell: ({ row }) => (
      <span className="flex items-center gap-2">
        <Owner account={row.original} />
        {row.original.kind !== "person" && <TagBadge>{humanize(row.original.kind)}</TagBadge>}
      </span>
    ),
    meta: { className: "max-md:hidden" },
  },
  {
    accessorKey: "match_method",
    header: "Matched by",
    cell: ({ getValue }) => <span className="text-muted-foreground">{humanize(getValue() as string)}</span>,
    meta: { className: "hidden min-[88rem]:table-cell" },
  },
  {
    accessorKey: "last_seen_at",
    header: ({ column }) => <SortHeader column={column} title="Last seen" />,
    cell: ({ row }) => <RelativeTime value={row.original.removed_at ?? row.original.last_seen_at} />,
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
    cell: ({ row }) => <AccountMenu account={row.original} />,
    meta: { align: "right", className: "w-px" },
  },
];

export function AccountsTable({ accounts, emptyText }: { accounts: AccountOut[]; emptyText: string }) {
  return (
    <DataTable
      columns={columns}
      data={accounts}
      getRowId={(account) => account.id}
      rowClassName={(account) => (account.status === "removed" ? "opacity-55" : undefined)}
      empty={<EmptyState icon={KeyRoundIcon} title={emptyText} />}
    />
  );
}
