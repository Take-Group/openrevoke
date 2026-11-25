"use client";

import { ChevronDownIcon } from "lucide-react";
import { useState } from "react";

import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { fieldTriggerClass } from "@/components/ui/field-styles";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export interface SearchableOption {
  value: string;
  label: string;
  /** Muted text on the right (e.g. a UTC offset). */
  hint?: string;
  /** Extra words the search matches (e.g. a currency name). */
  keywords?: string[];
}

export interface SearchableGroup {
  heading?: string;
  options: SearchableOption[];
}

interface SearchableSelectProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  groups: SearchableGroup[];
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  disabled?: boolean;
  className?: string;
}

function normalize(text: string): string {
  return text.toLowerCase().replaceAll("ł", "l").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/** Every word of the search must appear in the value or a keyword (no fuzzy matches). */
function matches(value: string, search: string, keywords?: string[]): number {
  const haystack = normalize([value, ...(keywords ?? [])].join(" ").replaceAll("_", " "));
  return normalize(search)
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word))
    ? 1
    : 0;
}

/** A field that opens a list with a search box on top. Type to filter, arrows and Enter to pick. */
export function SearchableSelect({
  id,
  value,
  onChange,
  groups,
  placeholder = "Select",
  searchPlaceholder = "Search",
  emptyText = "Nothing found",
  disabled,
  className,
}: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const selected = groups.flatMap((group) => group.options).find((option) => option.value === value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        disabled={disabled}
        render={<button type="button" id={id} className={cn(fieldTriggerClass, className)} />}
      >
        <span className={cn("min-w-0 flex-1 truncate text-left", !selected && "text-muted-foreground")}>
          {selected ? selected.label : value || placeholder}
        </span>
        {selected?.hint && <span className="shrink-0 text-xs text-muted-foreground tabular-nums">{selected.hint}</span>}
        <ChevronDownIcon className="text-muted-foreground" />
      </PopoverTrigger>
      <PopoverContent align="start" className="w-(--anchor-width) min-w-72 gap-0 p-0">
        <Command filter={matches}>
          <CommandInput autoFocus placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyText}</CommandEmpty>
            {groups.map((group, index) =>
              group.options.length === 0 ? null : (
                <CommandGroup key={group.heading ?? index} heading={group.heading}>
                  {group.options.map((option) => (
                    <CommandItem
                      key={option.value}
                      value={option.value}
                      keywords={[option.label, ...(option.keywords ?? [])]}
                      data-checked={option.value === value}
                      className="cursor-pointer"
                      onSelect={() => {
                        onChange(option.value);
                        setOpen(false);
                      }}
                    >
                      {/* The label takes the free width, so the hint lines up right before the check column. */}
                      <span className="min-w-0 flex-1 truncate">{option.label}</span>
                      {option.hint && (
                        <span className="shrink-0 text-right text-xs text-muted-foreground tabular-nums">{option.hint}</span>
                      )}
                    </CommandItem>
                  ))}
                </CommandGroup>
              ),
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
