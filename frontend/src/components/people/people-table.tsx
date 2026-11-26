"use client";

import { useRouter } from "next/navigation";
import { CopyIcon, HistoryIcon, SquareArrowOutUpRightIcon, UsersIcon } from "lucide-react";
import type { DataColumn } from "@/components/data-table/features";
import { toast } from "sonner";

import { AppAvatar, PersonAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { ConvertedTotal } from "@/components/common/converted-money";
import { StatusBadge } from "@/components/common/status-badge";
import { SortHeader } from "@/components/data-table/column-header";
import { DataTable } from "@/components/data-table/data-table";
import { RowActions } from "@/components/data-table/row-actions";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { amountOf, fullName } from "@/lib/format";
import type { AppRef, PersonListItem } from "@/lib/api/types";

const MAX_APPS = 5;

function AppStack({ apps }: { apps: AppRef[] }) {
  if (apps.length === 0) return <span className="text-muted-foreground">—</span>;
  const shown = apps.slice(0, MAX_APPS);
  return (
    <div className="flex items-center -space-x-1">
      {shown.map((app) => (
        <AppAvatar key={app.app_id} name={app.name} slug={app.slug} logoUrl={app.logo_url} size="xs" className="ring-2 ring-card" />
      ))}
      {apps.length > shown.length && (
        <span className="ml-2! text-xs text-muted-foreground tabular-nums">+{apps.length - shown.length}</span>
      )}
    </div>
  );
}

function PersonRowActions({ person }: { person: PersonListItem }) {
  const router = useRouter();
  return (
    <RowActions>
      <DropdownMenuItem onClick={() => router.push(`/people/${person.id}`)}>
        <SquareArrowOutUpRightIcon />
        Open
      </DropdownMenuItem>
      <DropdownMenuItem onClick={() => router.push(`/audit?person=${person.id}`)}>
        <HistoryIcon />
        History
      </DropdownMenuItem>
      <DropdownMenuItem
        onClick={() => navigator.clipboard.writeText(person.primary_email).then(() => toast.success("E-mail copied"))}
      >
        <CopyIcon />
        Copy e-mail
      </DropdownMenuItem>
    </RowActions>
  );
}

const columns: DataColumn<PersonListItem>[] = [
  {
    id: "name",
    accessorFn: (person) => fullName(person),
    header: ({ column }) => <SortHeader column={column} title="Person" />,
    cell: ({ row: { original: person } }) => (
      <div className="flex min-w-0 items-center gap-2.5">
        <PersonAvatar firstName={person.first_name} lastName={person.last_name} email={person.primary_email} size="sm" />
        <div className="min-w-0 leading-tight">
          <div className="truncate font-medium">{fullName(person)}</div>
          <div className="truncate text-xs text-muted-foreground">{person.primary_email}</div>
        </div>
      </div>
    ),
    meta: { className: "w-[34%]" },
  },
  {
    accessorKey: "employee_code",
    header: ({ column }) => <SortHeader column={column} title="Code" />,
    cell: ({ getValue }) => <span className="text-muted-foreground">{(getValue() as string | null) ?? "—"}</span>,
    meta: { className: "max-md:hidden w-28" },
  },
  {
    accessorKey: "status",
    header: ({ column }) => <SortHeader column={column} title="Status" />,
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
    meta: { className: "w-28" },
  },
  {
    id: "apps",
    accessorFn: (person) => person.apps.length,
    header: ({ column }) => <SortHeader column={column} title="Apps" />,
    cell: ({ row }) => <AppStack apps={row.original.apps} />,
    meta: { className: "max-md:hidden w-40" },
  },
  {
    id: "cost",
    accessorFn: (person) => amountOf(person.monthly_cost_total ?? person.monthly_cost[0]),
    header: ({ column }) => <SortHeader column={column} title="Monthly" />,
    cell: ({ row }) => (
      <ConvertedTotal total={row.original.monthly_cost_total} parts={row.original.monthly_cost} className="items-end" />
    ),
    meta: { align: "right", className: "max-md:hidden w-36" },
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => <PersonRowActions person={row.original} />,
    meta: { align: "right", className: "w-px" },
  },
];

export function PeopleTable({ people, filtered }: { people: PersonListItem[]; filtered: boolean }) {
  return (
    <DataTable
      columns={columns}
      data={people}
      getRowId={(person) => person.id}
      rowHref={(person) => `/people/${person.id}`}
      rowClassName={(person) => (person.status === "left" ? "text-muted-foreground" : undefined)}
      empty={<EmptyState icon={UsersIcon} title={filtered ? "No matches" : "No people yet"} />}
    />
  );
}
