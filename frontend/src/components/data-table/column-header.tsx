"use client";

import { ArrowDownIcon, ArrowUpIcon, ChevronsUpDownIcon } from "lucide-react";
import type { Column } from "@tanstack/react-table";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Header label that sorts the column on click. */
export function SortHeader<TData, TValue>({ column, title }: { column: Column<TData, TValue>; title: string }) {
  const sorted = column.getIsSorted();
  const Icon = sorted === "asc" ? ArrowUpIcon : sorted === "desc" ? ArrowDownIcon : ChevronsUpDownIcon;
  return (
    <Button
      variant="ghost"
      size="xs"
      onClick={() => column.toggleSorting(sorted === "asc")}
      className={cn(
        "group/sort -mx-2 text-muted-foreground",
        column.columnDef.meta?.align === "right" && "flex-row-reverse",
        sorted && "text-foreground",
      )}
    >
      {title}
      <Icon className={cn("size-3", !sorted && "opacity-0 transition-opacity group-hover/sort:opacity-60")} />
    </Button>
  );
}
