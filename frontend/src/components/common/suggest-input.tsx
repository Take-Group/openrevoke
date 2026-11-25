"use client";

import { Autocomplete } from "@base-ui/react/autocomplete";

import { Input } from "@/components/ui/input";
import { listItemClass, listPopupClass } from "@/components/ui/field-styles";

interface SuggestInputProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  /** Values offered under the field; the user may still type any other. */
  suggestions: readonly string[];
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
}

/**
 * A text field with a list of suggestions that filters as you type. Use it
 * instead of `<datalist>`, which the browser draws in its own style.
 */
export function SuggestInput({ id, value, onChange, suggestions, placeholder, required, disabled }: SuggestInputProps) {
  return (
    <Autocomplete.Root items={suggestions} value={value} onValueChange={(next) => onChange(next)} openOnInputClick>
      <Autocomplete.Input
        render={<Input id={id} placeholder={placeholder} required={required} disabled={disabled} autoComplete="off" spellCheck={false} />}
      />
      {suggestions.length > 0 && (
        <Autocomplete.Portal>
          <Autocomplete.Positioner sideOffset={4} align="start" className="isolate z-50">
            <Autocomplete.Popup className={`${listPopupClass} max-h-72 data-empty:hidden`}>
              <Autocomplete.List>
                {(item: string) => (
                  <Autocomplete.Item key={item} value={item} className={listItemClass}>
                    <span className="min-w-0 flex-1 truncate">{item}</span>
                  </Autocomplete.Item>
                )}
              </Autocomplete.List>
            </Autocomplete.Popup>
          </Autocomplete.Positioner>
        </Autocomplete.Portal>
      )}
    </Autocomplete.Root>
  );
}
