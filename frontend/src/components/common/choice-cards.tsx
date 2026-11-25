"use client";

import { CheckIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export interface ChoiceOption<T extends string> {
  value: T;
  label: string;
  /** One muted line under the label; leave out for a one-line card. */
  hint?: string;
  /** Mark before the label (`AppAvatar size="sm"`, `GlyphAvatar size="sm"`). */
  icon?: React.ReactNode;
}

/** Pick one of a few options shown as cards with a title and a hint (first-run questions). */
export function ChoiceCards<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: ChoiceOption<T>[];
  value: T | null;
  onChange: (value: T) => void;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-col gap-2">
      {options.map((option) => {
        const checked = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={checked}
            onClick={() => onChange(option.value)}
            className={cn(
              "flex gap-3 rounded-lg border border-frame px-3.5 py-2.5 text-left outline-none transition-colors hover:bg-subtle focus-visible:ring-2 focus-visible:ring-brand/40",
              option.hint ? "items-start" : "items-center",
              checked && "border-brand bg-brand-soft/40",
            )}
          >
            <span
              className={cn(
                "flex size-4 shrink-0 items-center justify-center rounded-full border",
                option.hint && "mt-0.5",
                checked && "border-brand bg-brand text-brand-foreground",
              )}
            >
              {checked && <CheckIcon className="size-3" />}
            </span>
            {option.icon}
            <span>
              <span className="block text-sm font-medium">{option.label}</span>
              {option.hint && <span className="block text-[0.8125rem] text-muted-foreground">{option.hint}</span>}
            </span>
          </button>
        );
      })}
    </div>
  );
}
