import type { ExchangeRatesInfo } from "@/lib/api/types";

/** "2026-11-23" -> "23.11.2026" (no time zone shift: it is a calendar day). */
export function formatRatesDay(day: string): string {
  const [year, month, date] = day.split("-");
  return `${date}.${month}.${year}`;
}

const SOURCE_LABEL: Record<string, string> = {
  "exchangerate-api": "Exchange Rate API",
  "currency-api": "fawazahmed0/exchange-api",
};

/** "Rates of 23.11.2026 by Exchange Rate API": the source's terms ask for a visible link. */
export function RatesSource({ info, className }: { info: ExchangeRatesInfo | null | undefined; className?: string }) {
  if (!info) return <span className={className}>No exchange rates yet</span>;
  const label = SOURCE_LABEL[info.source] ?? info.source;
  return (
    <span className={className}>
      Rates of {formatRatesDay(info.rates_date)} by{" "}
      {info.source_url ? (
        <a href={info.source_url} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline">
          {label}
        </a>
      ) : (
        label
      )}
    </span>
  );
}
