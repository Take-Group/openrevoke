"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type { CurrencyList, ExchangeRatesInfo } from "@/lib/api/types";

/** All currencies the organization can use, and the newest stored rates. Public (the setup needs it). */
export function useCurrencies() {
  return useQuery({
    queryKey: ["currencies"],
    queryFn: () => apiGet<CurrencyList>("/api/currencies"),
    staleTime: 10 * 60_000,
  });
}

export function useRefreshRates() {
  return useApiMutation({
    mutationFn: () => apiSend<ExchangeRatesInfo>("POST", "/api/exchange-rates/refresh"),
    // Converted amounts are everywhere: refresh every list with costs.
    invalidate: ["currencies", "apps", "app", "people", "person", "accounts"],
    success: (info) => `Rates of ${info.rates_date} downloaded (${info.currencies} currencies)`,
  });
}
