"use client";

import { useState } from "react";
import { ChevronDownIcon, ChevronsUpDownIcon, UserPlusIcon, UserXIcon } from "lucide-react";

import { PersonAvatar } from "@/components/common/avatars";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { fieldTriggerClass } from "@/components/ui/field-styles";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { usePeople } from "@/hooks/use-people";
import { fullName } from "@/lib/format";
import type { PersonListItem, PersonRef } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface PersonPickerProps {
  value: Pick<PersonRef, "first_name" | "last_name" | "primary_email"> | null;
  onChange: (person: PersonListItem | null) => void;
  /** Shows an "Unassign" entry. */
  allowClear?: boolean;
  placeholder?: string;
  disabled?: boolean;
  /** Bordered field (forms) instead of a quiet inline button (tables). */
  variant?: "inline" | "field";
  className?: string;
}

/** Opens a searchable list of people (server-side search), drawn like `SearchableSelect`. */
export function PersonPicker({
  value,
  onChange,
  allowClear,
  placeholder = "Assign",
  disabled,
  variant = "inline",
  className,
}: PersonPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const q = useDebouncedValue(search, 250);
  const people = usePeople({ q: q || undefined, limit: 20 }, open);

  const pick = (person: PersonListItem | null) => {
    onChange(person);
    setOpen(false);
    setSearch("");
  };

  const trigger =
    variant === "field" ? (
      <button type="button" className={cn(fieldTriggerClass, className)} />
    ) : (
      <Button variant="ghost" size="sm" className={cn("-ml-2 max-w-56 justify-start gap-2 px-2 font-normal", className)} />
    );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger disabled={disabled} render={trigger}>
        {value ? (
          <span className="flex min-w-0 flex-1 items-center gap-2">
            <PersonAvatar firstName={value.first_name} lastName={value.last_name} email={value.primary_email} size="xs" />
            <span className="truncate">{fullName(value)}</span>
          </span>
        ) : (
          <span className="flex min-w-0 flex-1 items-center gap-2 text-muted-foreground">
            <UserPlusIcon />
            <span className="truncate">{placeholder}</span>
          </span>
        )}
        {variant === "field" ? (
          <ChevronDownIcon className="text-muted-foreground" />
        ) : (
          <ChevronsUpDownIcon className="text-muted-foreground/60 opacity-0 transition-opacity group-hover/button:opacity-100" />
        )}
      </PopoverTrigger>
      <PopoverContent align="start" className="w-(--anchor-width) min-w-80 gap-0 p-0">
        <Command shouldFilter={false}>
          <CommandInput autoFocus placeholder="Search people" value={search} onValueChange={setSearch} />
          <CommandList>
            <CommandEmpty>{people.isPending ? "Loading…" : "No people found"}</CommandEmpty>
            <CommandGroup>
              {allowClear && value && (
                <CommandItem value="__unassign" className="cursor-pointer text-muted-foreground" onSelect={() => pick(null)}>
                  <UserXIcon />
                  Unassign
                </CommandItem>
              )}
              {people.data?.items.map((person) => (
                <CommandItem key={person.id} value={person.id} className="cursor-pointer" onSelect={() => pick(person)}>
                  <PersonAvatar firstName={person.first_name} lastName={person.last_name} email={person.primary_email} size="sm" />
                  <span className="min-w-0 leading-tight">
                    <span className="block truncate">
                      {fullName(person)}
                      {person.status === "left" && <span className="ml-1.5 text-muted-foreground">· left</span>}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">{person.primary_email}</span>
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
