// Currency names come from the browser (Intl), the codes from GET /api/currencies.

import type { SearchableGroup } from "@/components/common/searchable-select";

/** Shown first in the currency picker. */
export const POPULAR_CURRENCIES = ["USD", "EUR", "GBP", "CHF", "AUD"];

let names: Intl.DisplayNames | null = null;

/** "PLN" -> "Polish Zloty"; the code itself when the browser does not know it. */
export function currencyName(code: string): string {
  try {
    names ??= new Intl.DisplayNames(["en"], { type: "currency" });
    return names.of(code) ?? code;
  } catch {
    return code;
  }
}

/** The popular five in this order, then the rest alphabetically by code. Search matches the code and the name. */
export function currencyGroups(codes: readonly string[]): SearchableGroup[] {
  const option = (code: string) => ({ value: code, label: `${code} · ${currencyName(code)}`, keywords: [currencyName(code)] });
  const popular = POPULAR_CURRENCIES.filter((code) => codes.includes(code));
  return [
    { heading: "Popular", options: popular.map(option) },
    { heading: "All currencies", options: [...codes].sort().filter((code) => !popular.includes(code)).map(option) },
  ];
}
