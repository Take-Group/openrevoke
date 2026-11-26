"use client";

import { UsersIcon } from "lucide-react";

import { AppNames } from "@/components/access-profiles/profile-parts";
import { PersonAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { Hint } from "@/components/common/info-tip";
import { TONE_TEXT } from "@/components/common/status-badge";
import { SortHeader } from "@/components/data-table/column-header";
import { DataTable } from "@/components/data-table/data-table";
import type { DataColumn } from "@/components/data-table/features";
import type { AccessProfileMember } from "@/lib/api/access-profile-types";
import { formatWhen, fullName } from "@/lib/format";
import { cn } from "@/lib/utils";

const columns: DataColumn<AccessProfileMember>[] = [
  {
    id: "person",
    accessorFn: (member) => fullName(member.person),
    header: ({ column }) => <SortHeader column={column} title="Person" />,
    cell: ({ row: { original: member } }) => (
      <div className="flex min-w-0 items-center gap-2.5">
        <PersonAvatar
          firstName={member.person.first_name}
          lastName={member.person.last_name}
          email={member.person.primary_email}
          size="sm"
        />
        <span className="min-w-0 leading-tight">
          <span className="block truncate font-medium">{fullName(member.person)}</span>
          <span className="block truncate text-xs text-muted-foreground">{member.person.primary_email}</span>
        </span>
      </div>
    ),
    meta: { className: "w-full max-w-0 min-w-40" },
  },
  {
    id: "missing",
    accessorFn: (member) => member.missing.length,
    header: ({ column }) => <SortHeader column={column} title="Missing" />,
    cell: ({ row: { original: member } }) => (
      <span className={cn(member.missing.length > 0 && TONE_TEXT.warning)}>
        <AppNames apps={member.missing.map((item) => item.app)} />
      </span>
    ),
    meta: { className: "w-48" },
  },
  {
    id: "extra",
    accessorFn: (member) => member.extra.length,
    header: ({ column }) => <SortHeader column={column} title="Extra" />,
    cell: ({ row: { original: member } }) => (
      <Hint label="Accounts in apps outside all of the person's profiles">
        <span>
          <AppNames apps={member.extra.map((item) => item.app)} />
        </span>
      </Hint>
    ),
    meta: { className: "max-md:hidden w-48" },
  },
  {
    id: "roles",
    accessorFn: (member) => member.role_mismatch.length,
    header: "Other role",
    cell: ({ row: { original: member } }) =>
      member.role_mismatch.length === 0 ? (
        <span className="text-muted-foreground">—</span>
      ) : (
        <span className="truncate">
          {member.role_mismatch.map((item) => `${item.app.name}: ${item.role} (not ${item.expected_role})`).join(", ")}
        </span>
      ),
    meta: { className: "max-md:hidden w-48" },
  },
  {
    accessorKey: "assigned_at",
    header: ({ column }) => <SortHeader column={column} title="Assigned" />,
    cell: ({ row: { original: member } }) => (
      <Hint label={member.assigned_by ? `By ${member.assigned_by}` : "Assigned"}>
        <span className="text-muted-foreground">{formatWhen(member.assigned_at).split(",")[0]}</span>
      </Hint>
    ),
    meta: { className: "max-md:hidden w-28" },
  },
];

/** Members of a profile with what they miss, what they have outside their profiles and other roles. */
export function ProfileMembersTable({ members, empty }: { members: AccessProfileMember[]; empty: React.ReactNode }) {
  return (
    <DataTable
      columns={columns}
      data={members}
      getRowId={(member) => member.person.person_id}
      rowHref={(member) => `/people/${member.person.person_id}`}
      empty={empty ?? <EmptyState icon={UsersIcon} title="No members" />}
    />
  );
}
