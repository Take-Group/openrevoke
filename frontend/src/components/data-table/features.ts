import {
  createSortedRowModel,
  rowSortingFeature,
  sortFns,
  tableFeatures,
  type Column,
  type ColumnDef,
  type RowData,
} from "@tanstack/react-table";

/** Per-column options read by `DataTable` and `SortHeader`. */
export interface DataColumnMeta {
  /** Right-aligned column (money, counts). */
  align?: "right";
  /** Extra classes of the column's cells and header. */
  className?: string;
}

/**
 * TanStack Table 9 features of every panel table: client-side sorting only (search, filters and
 * paging stay on the server). Defined once, outside components, as TanStack recommends.
 */
export const dataTableFeatures = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns,
  columnMeta: {} as DataColumnMeta,
});

export type DataTableFeatures = typeof dataTableFeatures;

/** A column of a `DataTable`; use it instead of TanStack's `ColumnDef`. */
// TanStack needs `any` for the value type: every column has its own.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type DataColumn<TData extends RowData, TValue = any> = ColumnDef<DataTableFeatures, TData, TValue>;

export type DataTableColumn<TData extends RowData, TValue> = Column<DataTableFeatures, TData, TValue>;
