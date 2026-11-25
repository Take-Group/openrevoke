"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { flexRender, useTable, type RowData, type SortingState } from "@tanstack/react-table";

import { EmptyState } from "@/components/common/empty-state";
import { dataTableFeatures, type DataColumn } from "@/components/data-table/features";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

/** Clicks on these do their own thing and never open the row. */
const INTERACTIVE = "a,button,input,select,textarea,label,[role=menuitem],[role=option],[data-row-ignore]";

interface DataTableProps<TData extends RowData> {
  columns: DataColumn<TData>[];
  data: TData[];
  getRowId: (row: TData) => string;
  /** Row click opens this address (Ctrl or Cmd click: a new tab). */
  rowHref?: (row: TData) => string | null;
  rowClassName?: (row: TData) => string | undefined;
  /** Shown in place of the rows when there are none. */
  empty?: React.ReactNode;
  initialSorting?: SortingState;
  className?: string;
}

/**
 * The shadcn/ui data-table pattern on TanStack Table: sortable columns, sticky
 * header under the top bar, row click to the detail page. Search, filters and
 * paging stay on the server (hooks), sorting works on the loaded page.
 */
export function DataTable<TData extends RowData>({
  columns,
  data,
  getRowId,
  rowHref,
  rowClassName,
  empty,
  initialSorting = [],
  className,
}: DataTableProps<TData>) {
  const router = useRouter();
  const [sorting, setSorting] = useState<SortingState>(initialSorting);
  const table = useTable({
    features: dataTableFeatures,
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getRowId: (row) => getRowId(row),
  });

  const open = (event: React.MouseEvent<HTMLTableRowElement>, href: string | null) => {
    const target = event.target as HTMLElement;
    // Portaled popups (menus, dialogs) bubble through React but are not inside the row.
    if (!href || !event.currentTarget.contains(target) || target.closest(INTERACTIVE)) return;
    if (window.getSelection()?.toString()) return;
    if (event.metaKey || event.ctrlKey) window.open(href, "_blank");
    else router.push(href);
  };

  const rows = table.getRowModel().rows;
  return (
    <div className={cn("overflow-clip rounded-lg border border-frame bg-card shadow-card", className)}>
      <Table containerClassName="max-md:overflow-x-auto md:overflow-visible">
        <TableHeader>
          {table.getHeaderGroups().map((group) => (
            <TableRow key={group.id} className="hover:bg-transparent">
              {group.headers.map((header) => {
                const meta = header.column.columnDef.meta;
                return (
                  <TableHead
                    key={header.id}
                    className={cn(
                      "sticky top-0 z-10 h-9 bg-subtle px-3 text-xs font-medium text-muted-foreground first:rounded-tl-[6px] first:pl-4 last:rounded-tr-[6px] last:pr-4",
                      meta?.align === "right" && "text-right",
                      meta?.className,
                    )}
                  >
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                );
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={columns.length} className="p-0">
                {empty ?? <EmptyState title="Nothing here" />}
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => {
              const href = rowHref?.(row.original) ?? null;
              return (
                <TableRow
                  key={row.id}
                  onClick={href ? (event) => open(event, href) : undefined}
                  className={cn(href && "cursor-pointer", rowClassName?.(row.original))}
                >
                  {row.getAllCells().map((cell) => {
                    const meta = cell.column.columnDef.meta;
                    return (
                      <TableCell
                        key={cell.id}
                        className={cn(
                          "h-11 px-3 py-2 first:pl-4 last:pr-4",
                          meta?.align === "right" && "text-right tabular-nums",
                          meta?.className,
                        )}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    );
                  })}
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </div>
  );
}
