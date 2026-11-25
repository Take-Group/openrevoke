"use client";

import { SearchIcon, XIcon } from "lucide-react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchInput({ value, onChange, placeholder = "Search", className }: SearchInputProps) {
  return (
    <div className={cn("relative w-full sm:w-64", className)}>
      <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 z-10 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        aria-label={placeholder}
        className="pr-7 pl-8 [&::-webkit-search-cancel-button]:hidden"
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      {value && (
        <button
          type="button"
          aria-label="Clear search"
          className="absolute top-1/2 right-2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          onClick={() => onChange("")}
        >
          <XIcon className="size-3.5" />
        </button>
      )}
    </div>
  );
}

/** Row of filters above a table. */
export function Toolbar({ children, actions }: { children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <div className="flex max-w-full min-w-0 flex-wrap items-center gap-2">{children}</div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
