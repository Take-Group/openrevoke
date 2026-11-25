# Skill: organization currency and converted amounts (frontend)

Backend: `skills/backend/exchange-rates.md`.

## Files

| File | Role |
|---|---|
| `frontend/src/components/common/converted-money.tsx` | `ConvertedMoney` (amount), `ConvertedPrice` (price with a period) and `ConvertedTotal` (total) in the organization currency; the original below only with `showOriginal`; without a rate, the original with a warning |
| `frontend/src/components/common/searchable-select.tsx` | own list with a search box at the top (Popover and cmdk), groups, a hint on the right; used by the currency and time zone selects |
| `frontend/src/components/common/currency-select.tsx` | all currencies from `GET /api/currencies`, popular ones at the top, search by code and name |
| `frontend/src/components/common/time-zone-select.tsx`, `frontend/src/lib/time-zones.ts` | IANA zones from the browser (`Intl.supportedValuesOf`), this computer's zone at the top, UTC offset |
| `frontend/src/components/common/rates-source.tsx` | "Rates of DD.MM.YYYY by …" with a link to the source (required by the ExchangeRate-API terms) |
| `frontend/src/lib/currencies.ts` | currency names from `Intl.DisplayNames`, option order |
| `frontend/src/hooks/use-currencies.ts` | `useCurrencies`, `useRefreshRates` |

## Where amounts are

Rule: everywhere in the panel, amounts are only in the organization
currency, converted at the latest rate. The price and cost in the currency the
app bills in are only on the app details page (`showOriginal`
in the "Price" and "Monthly cost" stats, price settings and billing).

App tables ("Price" columns from `price_converted` and "Monthly"), account
and people tables, person details, the "Monthly cost" card and "Cost by app" on the
dashboard. Each place takes `*_converted` or `*_total`, and when it is
`null` (no rate), it shows the original with a warning. Sorting uses the converted
amount when there is one.

Settings (`/settings`): organization currency, rate source and date,
"Refresh rates" for an admin. The app price form has the same currency
choice; a new app starts in the organization currency.
