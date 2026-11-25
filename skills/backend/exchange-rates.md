# Skill: exchange rates and cost conversion (backend)

## What it does

The panel shows costs in the organization currency (the first admin picks it
in setup, an admin changes it in `/settings`). We fetch rates once a day
from free sources without a key. The amount in the app's original currency
stays in the response next to the converted one. Since 23.11.2026.

- Source 1: ExchangeRate-API "Open Access"
  (`https://open.er-api.com/v6/latest/EUR`), 166 ISO 4217 currencies, new
  rates once a day at about 00:00 UTC. Terms: a visible link "Rates by
  Exchange Rate API" and no more often than once an hour.
- Source 2 (fallback, when 1 does not respond): `fawazahmed0/exchange-api`
  on jsDelivr, CC0. It also has crypto and metals; we take only ISO codes.
- Organization currency: any code from `app/services/currencies.py`
  (166 codes, a fixed list, works before the first fetch and offline).
- No rate for the app's currency: `*_converted` and `*_total` are `null`,
  and the panel shows the original amount with a warning. A total without a rate for
  one of the currencies is also `null`: a partial total would mislead.

## Files

| File | Role |
|---|---|
| `backend/app/exchange_rates/providers.py` | `RateProvider`, two sources, parsing, conversion to an EUR base |
| `backend/app/services/exchange_rates.py` | `refresh` (the first source that responds), `store` (upsert of the day), `latest_info`, `load_converter` |
| `backend/app/services/conversion.py` | `Converter`: `convert`, `total`; pure logic, no database |
| `backend/app/services/currencies.py` | list of ISO 4217 codes |
| `backend/app/models/exchange_rate.py` | table `exchange_rate`: day, currency, `per_eur`, source |
| `backend/app/temporal/rates_workflow.py`, `rates_activities.py`, `rates_schedule.py` | `RefreshExchangeRatesWorkflow`, schedule `exchange-rates-daily` (cron `30 2 * * *` UTC), fetch at worker start when there are no rates from today |
| `backend/app/api/currencies.py` | `GET /api/currencies` (public, setup needs it), `POST /api/exchange-rates/refresh` (admin) |

## Flow

1. At start the worker calls `ensure_rates`: it creates or updates
   the schedule and, when the database has no rates from today's UTC date,
   starts the workflow at once.
2. The activity calls `exchange_rates.refresh`: it fetches the rates and stores a row
   per currency for the day from the source (upsert, a repeated fetch overwrites).
   Both sources fail: the workflow retries up to 6 times, and the old rates stay.
3. Services that return costs (`apps`, `people`, `accounts`,
   `dashboard`) call `load_converter` once per request and pass it
   to the presenters. Rate: the newest day in the table.
4. Fields in the API: `price` (original) and `price_converted` (app),
   `monthly_cost` (original) and `monthly_cost_converted`
   (app, account), `monthly_cost` (list per currency)
   and `monthly_cost_total` (person, dashboard), `exchange_rates` in the dashboard.

## How to extend

- New source: a class with `name`, `attribution_url` and `fetch(http)` that returns
  a `RateSnapshot` with rates per 1 EUR, added to `DEFAULT_PROVIDERS`,
  plus a label in `ATTRIBUTION` and in `frontend/src/components/common/rates-source.tsx`.
- Rate from the invoice day instead of the newest one: `exchange_rate` keeps the history,
  so it is enough to read the row from the chosen day.
