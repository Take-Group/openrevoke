"use client";

import { MoreHorizontalIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

/** The "..." menu at the end of a row. Children are DropdownMenuItem elements. */
export function RowActions({ children, label = "Row actions" }: { children: React.ReactNode; label?: string }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={<Button variant="ghost" size="icon-sm" aria-label={label} className="text-muted-foreground" />}
      >
        <MoreHorizontalIcon />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {children}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
