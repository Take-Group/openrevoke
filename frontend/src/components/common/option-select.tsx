"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
}

interface OptionSelectProps<T extends string> {
  id?: string;
  /** "" means nothing chosen: the trigger shows the placeholder. */
  value: T | "";
  onChange: (value: T | "") => void;
  options: readonly SelectOption<T>[];
  /** Text shown when nothing is chosen. Unless `required`, it is also the first item and clears the choice. */
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  name?: string;
  className?: string;
  "aria-label"?: string;
}

/**
 * The one dropdown of the panel: a list of options, no search. Use
 * `SearchableSelect` when the list is long (currencies, time zones) and
 * `PersonPicker` for people.
 */
export function OptionSelect<T extends string>({
  id,
  value,
  onChange,
  options,
  placeholder,
  required,
  disabled,
  name,
  className,
  "aria-label": ariaLabel,
}: OptionSelectProps<T>) {
  const clearable = placeholder !== undefined && !required;
  const items = [...(clearable ? [{ value: null, label: placeholder }] : []), ...options];
  return (
    <Select<T | null>
      id={id}
      name={name}
      items={items}
      value={value === "" ? null : value}
      onValueChange={(next) => onChange(next ?? "")}
      required={required}
      disabled={disabled}
    >
      <SelectTrigger className={className} aria-label={ariaLabel}>
        <SelectValue placeholder={placeholder ?? "Select"} />
      </SelectTrigger>
      <SelectContent>
        {items.map((option) => (
          <SelectItem key={option.value ?? ""} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
