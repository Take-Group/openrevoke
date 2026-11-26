"use client";

import { HandIcon, ImageIcon, ListChecksIcon, SparklesIcon, UserMinusIcon, UserPlusIcon, UserXIcon } from "lucide-react";
import type { DataColumn } from "@/components/data-table/features";

import { ActionButtons } from "@/components/actions/action-buttons";
import { AppAvatar, PersonAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { Hint, InfoTip } from "@/components/common/info-tip";
import { RecordLink, TextLink } from "@/components/common/links";
import { RelativeTime } from "@/components/common/relative-time";
import { Spinner } from "@/components/common/spinner";
import { StatusBadge, TagBadge } from "@/components/common/status-badge";
import { SortHeader } from "@/components/data-table/column-header";
import { DataTable } from "@/components/data-table/data-table";
import { isMoving } from "@/hooks/use-actions";
import { accountLabel, actionOperation, fullName, humanize } from "@/lib/format";
import type { ActionOut } from "@/lib/api/types";

const OPERATION_ICON = {
  manual_task: HandIcon,
  create_account: UserPlusIcon,
  delete_account: UserMinusIcon,
  suspend_account: UserXIcon,
} as const;

const OPERATION_SHORT: Record<keyof typeof OPERATION_ICON, string> = {
  manual_task: "Task",
  create_account: "Add",
  delete_account: "Remove",
  suspend_account: "Suspend",
};

/** Short verb with an icon; the full operation is in the tooltip. */
function Operation({ action }: { action: ActionOut }) {
  const operation = action.kind === "manual_task" ? action.payload.operation : action.kind;
  const key = operation === "delete_account" && action.suspends ? "suspend_account" : (operation ?? "manual_task");
  const Icon = action.kind === "manual_task" ? HandIcon : OPERATION_ICON[key as keyof typeof OPERATION_ICON];
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <Hint label={actionOperation(action)}>
        <span className="inline-flex items-center gap-1.5">
          <Icon className="size-3.5 text-muted-foreground" />
          {OPERATION_SHORT[key as keyof typeof OPERATION_SHORT] ?? "Task"}
        </span>
      </Hint>
      {action.kind === "manual_task" && <InfoTip>Manual task: do it in the app, then mark it done.</InfoTip>}
    </span>
  );
}

/** Exactly what will be sent: the account or e-mail, and the role. */
function Target({ action }: { action: ActionOut }) {
  const account = action.account ? accountLabel(action.account) : null;
  const main = account ?? action.payload.email ?? null;
  const extraEmail = account && action.payload.email && action.payload.email !== account ? action.payload.email : null;
  if (!main && !action.payload.role) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="flex min-w-0 items-center gap-2">
      <span className="min-w-0 truncate">{main}</span>
      {extraEmail && <span className="truncate text-xs text-muted-foreground">{extraEmail}</span>}
      {action.payload.role && <TagBadge className="shrink-0">{action.payload.role}</TagBadge>}
    </span>
  );
}

/** What happens to the action now, next to its status badge. */
function progressText(action: ActionOut): string | null {
  if (action.status === "running") return "Writing to the app";
  if (action.status === "verifying") return "Checking the result";
  if (action.status === "approved") return action.kind === "manual_task" ? "Waiting for you" : "Starting";
  if (action.status === "done" && action.kind !== "manual_task") return "Confirmed by a read";
  return null;
}

function ActionStatus({ action }: { action: ActionOut }) {
  const text = progressText(action);
  return (
    <div className="flex flex-col items-start gap-0.5">
      <StatusBadge status={action.status} />
      {text && (
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          {isMoving(action) && <Spinner className="size-3 text-current" />}
          {text}
        </span>
      )}
      {action.error && action.status !== "done" && (
        <Hint label={action.error}>
          <span className="block max-w-56 truncate text-xs text-destructive">{action.error}</span>
        </Hint>
      )}
      {action.has_screenshot && (
        <TextLink external href={`/api/actions/${action.id}/screenshot`} className="inline-flex items-center gap-1 text-xs">
          <ImageIcon className="size-3" />
          Where it stopped
        </TextLink>
      )}
      <RecipeFixes action={action} />
    </div>
  );
}

const FIX_TEXT = { active: "AI fixed step", proposed: "AI proposes a fix for step", rejected: "AI fix rejected for step" };

/** Click recipe steps the AI repaired during this action; the note is in the tooltip. */
function RecipeFixes({ action }: { action: ActionOut }) {
  if (action.recipe_fixes.length === 0) return null;
  return action.recipe_fixes.map((fix) => (
    <Hint key={fix.id} label={fix.note}>
      <span className="flex max-w-56 items-center gap-1 truncate text-xs text-muted-foreground">
        <SparklesIcon className="size-3 shrink-0" />
        {FIX_TEXT[fix.status]} “{fix.step_id}”
      </span>
    </Hint>
  ));
}

const columns: DataColumn<ActionOut>[] = [
  {
    id: "app",
    accessorFn: (action) => action.app.name,
    header: ({ column }) => <SortHeader column={column} title="App" />,
    cell: ({ row: { original: action } }) => (
      <div className="flex items-center gap-2.5">
        <AppAvatar name={action.app.name} slug={action.app.slug} size="sm" />
        <span className="font-medium">{action.app.name}</span>
      </div>
    ),
  },
  {
    id: "operation",
    accessorFn: (action) => actionOperation(action),
    header: ({ column }) => <SortHeader column={column} title="Operation" />,
    cell: ({ row }) => <Operation action={row.original} />,
  },
  {
    id: "person",
    accessorFn: (action) => (action.person ? fullName(action.person) : ""),
    header: ({ column }) => <SortHeader column={column} title="Person" />,
    cell: ({ row: { original: action } }) =>
      action.person ? (
        <RecordLink href={`/people/${action.person.person_id}`} className="inline-flex items-center gap-2">
          <PersonAvatar
            firstName={action.person.first_name}
            lastName={action.person.last_name}
            email={action.person.primary_email}
            size="xs"
          />
          {fullName(action.person)}
        </RecordLink>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
    meta: { className: "max-md:hidden" },
  },
  {
    id: "target",
    header: "Target",
    cell: ({ row }) => <Target action={row.original} />,
    meta: { className: "max-md:hidden w-full max-w-0 min-w-32" },
  },
  {
    accessorKey: "reason",
    header: "Reason",
    cell: ({ row }) => <TagBadge>{humanize(row.original.reason)}</TagBadge>,
    meta: { className: "hidden 2xl:table-cell" },
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <ActionStatus action={row.original} />,
  },
  {
    id: "approved_by",
    header: "Approved by",
    cell: ({ row: { original: action } }) => (
      <span className="block truncate text-muted-foreground" title={action.created_by ? `Asked by ${action.created_by}` : undefined}>
        {action.approved_by ?? "—"}
      </span>
    ),
    meta: { className: "hidden xl:table-cell max-w-48" },
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => <SortHeader column={column} title="Created" />,
    cell: ({ row }) => <RelativeTime value={row.original.created_at} />,
    meta: { className: "hidden min-[88rem]:table-cell" },
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => <ActionButtons action={row.original} />,
    meta: { align: "right", className: "w-px" },
  },
];

export function ActionsTable({ actions, emptyText }: { actions: ActionOut[]; emptyText: string }) {
  return (
    <DataTable
      columns={columns}
      data={actions}
      getRowId={(action) => action.id}
      empty={<EmptyState icon={ListChecksIcon} title={emptyText} />}
    />
  );
}
