"use client";

import { SearchableSelect } from "@/components/common/searchable-select";
import { useCurrencies } from "@/hooks/use-currencies";
import { currencyGroups } from "@/lib/currencies";

interface CurrencySelectProps {
  id: string;
  value: string;
  onChange: (code: string) => void;
  disabled?: boolean;
}

/** Every currency the API knows (ISO 4217), popular ones first, with a search box (code or name). */
export function CurrencySelect({ id, value, onChange, disabled }: CurrencySelectProps) {
  const currencies = useCurrencies();
  const codes = currencies.data?.codes ?? [value];
  return (
    <SearchableSelect
      id={id}
      value={value}
      onChange={onChange}
      groups={currencyGroups(codes.includes(value) ? codes : [value, ...codes])}
      placeholder="Select a currency"
      searchPlaceholder="Search currency, e.g. PLN or zloty"
      emptyText="No such currency"
      disabled={disabled || currencies.isPending}
    />
  );
}
