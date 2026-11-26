"use client";

import { PlusIcon, ShieldCheckIcon } from "lucide-react";

import { AppLogos } from "@/components/access-profiles/profile-parts";
import { ConvertedTotal } from "@/components/common/converted-money";
import { EmptyState } from "@/components/common/empty-state";
import { Hint } from "@/components/common/info-tip";
import { LinkButton } from "@/components/common/links";
import { PageHeader } from "@/components/common/page-header";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { QueryState } from "@/components/common/query-state";
import { StatusDot, TONE_TEXT } from "@/components/common/status-badge";
import { SortHeader } from "@/components/data-table/column-header";
import { DataTable } from "@/components/data-table/data-table";
import type { DataColumn } from "@/components/data-table/features";
import { useAccessProfiles } from "@/hooks/use-access-profiles";
import type { AccessProfileOut } from "@/lib/api/access-profile-types";
import { amountOf } from "@/lib/format";
import { cn } from "@/lib/utils";

function NewProfileButton() {
  return (
    <LinkButton href="/access-profiles/new">
      <PlusIcon />
      New profile
    </LinkButton>
  );
}

const columns: DataColumn<AccessProfileOut>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => <SortHeader column={column} title="Profile" />,
    cell: ({ row: { original: profile } }) => (
      <span className="block min-w-0 leading-tight">
        <span className="block truncate font-medium">{profile.name}</span>
        {profile.description && (
          <span className="block truncate text-xs text-muted-foreground">{profile.description}</span>
        )}
      </span>
    ),
    meta: { className: "w-full max-w-0 min-w-40" },
  },
  {
    id: "apps",
    header: "Apps",
    cell: ({ row }) => <AppLogos apps={row.original.apps} />,
    meta: { className: "max-md:hidden" },
  },
  {
    accessorKey: "member_count",
    header: ({ column }) => <SortHeader column={column} title="People" />,
    cell: ({ row: { original: profile } }) => (
      <span className="inline-flex items-center justify-end gap-2 tabular-nums">
        {profile.members_missing_access > 0 && (
          <Hint label={`${profile.members_missing_access} miss access from this profile`}>
            <span className={cn("inline-flex items-center gap-1 text-xs", TONE_TEXT.warning)}>
              <StatusDot tone="warning" />
              {profile.members_missing_access}
            </span>
          </Hint>
        )}
        {profile.member_count}
      </span>
    ),
    meta: { align: "right", className: "w-24" },
  },
  {
    id: "cost",
    accessorFn: (profile) => amountOf(profile.cost_per_person_total),
    header: ({ column }) => <SortHeader column={column} title="Per person / mo" />,
    cell: ({ row: { original: profile } }) => (
      <ConvertedTotal total={profile.cost_per_person_total} parts={profile.cost_per_person} />
    ),
    meta: { align: "right", className: "max-md:hidden w-40" },
  },
];

/** `/access-profiles`: profiles with their apps, members and what one person costs. */
export function AccessProfilesView() {
  const query = useAccessProfiles();
  return (
    <>
      <PageHeader title="Access profiles" actions={<NewProfileButton />} />
      <QueryState query={query} loading={<TableSkeleton rows={4} />}>
        {(list) => (
          <DataTable
            columns={columns}
            data={list.items}
            getRowId={(profile) => profile.id}
            rowHref={(profile) => `/access-profiles/${profile.id}`}
            empty={<EmptyState icon={ShieldCheckIcon} title="No access profiles yet" action={<NewProfileButton />} />}
          />
        )}
      </QueryState>
    </>
  );
}
