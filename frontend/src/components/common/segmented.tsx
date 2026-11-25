"use client";

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";

export interface SegmentOption<T extends string> {
  value: T;
  label: React.ReactNode;
  /** Small number after the label. */
  count?: number;
  /** Highlights the count (e.g. accounts without owner). */
  attention?: boolean;
}

interface SegmentedProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: SegmentOption<T>[];
  label: string;
  className?: string;
}

/** Single-choice filter as a compact segmented control. */
export function Segmented<T extends string>({ value, onChange, options, label, className }: SegmentedProps<T>) {
  return (
    <ToggleGroup
      aria-label={label}
      value={[value]}
      // Clicking the active item would clear the group: keep one value selected.
      onValueChange={(next) => next[0] && onChange(next[0] as T)}
      spacing={0}
      className={cn("h-9 max-w-full min-w-0 overflow-x-auto rounded-lg border border-input bg-background p-[3px] [scrollbar-width:none]", className)}
    >
      {options.map((option) => (
        <ToggleGroupItem
          key={option.value}
          value={option.value}
          size="sm"
          className="h-[30px] rounded-md! border-0! px-2.5 text-[0.8125rem] text-muted-foreground hover:bg-transparent hover:text-foreground data-pressed:bg-accent data-pressed:text-foreground"
        >
          {option.label}
          {option.count !== undefined && option.count > 0 && (
            <span
              className={cn(
                "ml-0.5 tabular-nums text-muted-foreground",
                option.attention && "text-warning",
              )}
            >
              {option.count}
            </span>
          )}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}
