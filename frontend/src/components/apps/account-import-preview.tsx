import type { DataColumn } from "@/components/data-table/features";

import { StatusBadge } from "@/components/common/status-badge";
import { DataTable } from "@/components/data-table/data-table";
import type { AccountImportResult, AccountImportRow } from "@/lib/api/inventory-types";
import type { ImportRowAction } from "@/lib/api/types";

const ACTION_STATUS: Record<ImportRowAction, { status: string; label: string }> = {
  create: { status: "active", label: "Add" },
  update: { status: "update", label: "Update" },
  unchanged: { status: "cancelled", label: "Unchanged" },
  error: { status: "error", label: "Error" },
};

function accountLabel(row: AccountImportRow): string {
  return row.email ?? row.username ?? row.display_name ?? "—";
}

function RowDetails({ row }: { row: AccountImportRow }) {
  if (row.errors.length > 0) return <span className="text-destructive">{row.errors.join("; ")}</span>;
  if (row.changes.length > 0) {
    return (
      <ul className="flex flex-col gap-0.5">
        {row.changes.map((change) => (
          <li key={change.field}>
            <span className="text-muted-foreground">{change.field}:</span>{" "}
            {change.old !== null && <span className="text-muted-foreground line-through">{change.old}</span>}{" "}
            <span>{change.new ?? "(empty)"}</span>
          </li>
        ))}
      </ul>
    );
  }
  if (row.person) {
    return (
      <span>
        {row.person.first_name} {row.person.last_name}
      </span>
    );
  }
  return <span className="text-muted-foreground">{row.action === "create" ? "No person with this e-mail" : "—"}</span>;
}

function columns(showApp: boolean): DataColumn<AccountImportRow>[] {
  return [
    {
      accessorKey: "line",
      header: "Line",
      cell: ({ row }) => <span className="text-muted-foreground tabular-nums">{row.original.line}</span>,
      meta: { className: "max-md:hidden w-16" },
    },
    ...(showApp
      ? [
          {
            accessorKey: "app",
            header: "App",
            cell: ({ row }) => row.original.app || "—",
            meta: { className: "max-md:hidden" },
          } satisfies DataColumn<AccountImportRow>,
        ]
      : []),
    {
      id: "account",
      header: "Account",
      cell: ({ row }) => accountLabel(row.original),
      meta: { className: "w-full max-w-0 min-w-40 truncate" },
    },
    {
      accessorKey: "action",
      header: "Result",
      cell: ({ row }) => (
        <StatusBadge
          status={ACTION_STATUS[row.original.action].status}
          tone={row.original.action === "update" ? "info" : undefined}
          label={ACTION_STATUS[row.original.action].label}
        />
      ),
      meta: { className: "w-28" },
    },
    {
      id: "details",
      header: "Person or changes",
      cell: ({ row }) => <RowDetails row={row.original} />,
      meta: { className: "whitespace-normal max-md:hidden" },
    },
  ];
}

/** Counts and one row per line of a CSV or pasted list: what the import does (or did). */
export function AccountImportPreview({ result, showApp }: { result: AccountImportResult; showApp?: boolean }) {
  // Unchanged rows say nothing new: show them last.
  const rows = [...result.rows].sort((a, b) => Number(a.action === "unchanged") - Number(b.action === "unchanged"));
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">{result.dry_run ? "Preview" : "Imported"}</span>
        <StatusBadge status="active" label={`${result.created} new`} />
        <StatusBadge status="update" tone="info" label={`${result.updated} updated`} />
        <StatusBadge status="cancelled" label={`${result.unchanged} unchanged`} />
        {result.failed > 0 && <StatusBadge status="error" label={`${result.failed} skipped`} />}
      </div>
      {result.new_apps.length > 0 && (
        <p className="text-sm">
          <span className="text-muted-foreground">{result.dry_run ? "New apps to create:" : "New apps:"}</span>{" "}
          {result.new_apps.map((app) => app.name).join(", ")}
        </p>
      )}
      <DataTable
        columns={columns(Boolean(showApp))}
        data={rows}
        getRowId={(row) => String(row.line)}
        className="max-h-80 overflow-y-auto"
      />
    </div>
  );
}
