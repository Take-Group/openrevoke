import type { DataColumn } from "@/components/data-table/features";

import { StatusBadge } from "@/components/common/status-badge";
import { DataTable } from "@/components/data-table/data-table";
import type { ImportResult, ImportRowAction, ImportRowResult } from "@/lib/api/types";

const ACTION_STATUS: Record<ImportRowAction, { status: string; label: string }> = {
  create: { status: "active", label: "Create" },
  update: { status: "update", label: "Update" },
  unchanged: { status: "cancelled", label: "Unchanged" },
  error: { status: "error", label: "Error" },
};

/** A create row: the new person as the backend will save it. */
function NewPerson({ row }: { row: ImportRowResult }) {
  const name = [row.first_name, row.last_name].filter(Boolean).join(" ");
  const extra = [
    row.employee_code && `code ${row.employee_code}`,
    row.aliases && row.aliases.length > 0 && `aliases ${row.aliases.join(", ")}`,
  ].filter(Boolean);
  return (
    <span>
      <span className="font-medium">{name || "(no name)"}</span>
      {extra.length > 0 && <span className="text-muted-foreground"> · {extra.join(" · ")}</span>}
    </span>
  );
}

function RowDetails({ row }: { row: ImportRowResult }) {
  if (row.errors.length > 0) return <span className="text-destructive">{row.errors.join("; ")}</span>;
  if (row.action === "create") return <NewPerson row={row} />;
  if (row.changes.length === 0) return <span className="text-muted-foreground">—</span>;
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

const columns: DataColumn<ImportRowResult>[] = [
  {
    accessorKey: "line",
    header: "Line",
    cell: ({ row }) => <span className="text-muted-foreground tabular-nums">{row.original.line}</span>,
    meta: { className: "max-md:hidden w-16" },
  },
  {
    accessorKey: "email",
    header: "E-mail",
    cell: ({ row }) => row.original.email ?? "—",
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
    meta: { className: "whitespace-normal" },
  },
];

export function ImportPreview({ result }: { result: ImportResult }) {
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
      <DataTable columns={columns} data={rows} getRowId={(row) => String(row.line)} className="max-h-80 overflow-y-auto" />
    </div>
  );
}
