"use client";

import { useState } from "react";
import { ChevronDownIcon } from "lucide-react";

import { AppAvatar } from "@/components/common/avatars";
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { fieldTriggerClass } from "@/components/ui/field-styles";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useCatalogSearch } from "@/hooks/use-catalog";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { CatalogSearchItem } from "@/lib/api/catalog-types";
import { cn } from "@/lib/utils";

export function hostOf(url: string | null | undefined): string {
  if (!url) return "";
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** One catalog app in a list: logo, name, website, and why it is notable (added, found by discovery). */
export function CatalogItemLabel({ item }: { item: CatalogSearchItem }) {
  return (
    <>
      <AppAvatar name={item.name} catalogSlug={item.slug} logoUrl={item.logo_url} size="sm" />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{item.name}</span>
        <span className="block truncate text-xs text-muted-foreground">{hostOf(item.website)}</span>
      </span>
      {item.already_added ? (
        <span className="shrink-0 text-xs text-muted-foreground">Added</span>
      ) : item.discovered_users ? (
        <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
          {item.discovered_users} signed in
        </span>
      ) : null}
    </>
  );
}

interface CatalogAppPickerProps {
  id?: string;
  value: CatalogSearchItem | null;
  onChange: (item: CatalogSearchItem) => void;
  autoFocus?: boolean;
}

/**
 * Combobox over the app catalog (server search): logo, name and website per app. Apps already in
 * Open Revoke say "Added"; the caller decides what picking one does.
 */
export function CatalogAppPicker({ id, value, onChange, autoFocus }: CatalogAppPickerProps) {
  const [open, setOpen] = useState(Boolean(autoFocus));
  const [search, setSearch] = useState("");
  const q = useDebouncedValue(search.trim(), 200);
  const results = useCatalogSearch(q, 20, open);
  const items = results.data?.items ?? [];

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger render={<button type="button" id={id} className={fieldTriggerClass} />}>
        {value ? (
          <span className="flex min-w-0 flex-1 items-center gap-2">
            <AppAvatar name={value.name} catalogSlug={value.slug} logoUrl={value.logo_url} size="xs" />
            <span className="truncate">{value.name}</span>
          </span>
        ) : (
          <span className="min-w-0 flex-1 truncate text-left text-muted-foreground">Search 350+ known apps</span>
        )}
        <ChevronDownIcon className="text-muted-foreground" />
      </PopoverTrigger>
      <PopoverContent align="start" className="w-(--anchor-width) min-w-80 gap-0 p-0">
        <Command shouldFilter={false}>
          <CommandInput autoFocus placeholder="Slack, Notion, figma.com…" value={search} onValueChange={setSearch} />
          <CommandList className={cn(results.isFetching && "opacity-80")}>
            <CommandEmpty>{results.isLoading ? "Searching…" : "Not in the catalog"}</CommandEmpty>
            {items.map((item) => (
              <CommandItem
                key={item.slug}
                value={item.slug}
                className="cursor-pointer gap-2.5"
                onSelect={() => {
                  onChange(item);
                  setOpen(false);
                }}
              >
                <CatalogItemLabel item={item} />
              </CommandItem>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
