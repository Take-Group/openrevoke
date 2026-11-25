# open-revoke/frontend/src/lib/

Framework-free helpers of the panel: formatting, brand marks, time zones and the connection-form schema reader. Components import them with `@/lib/...`; the API client and its types are in `api/`.

- `api/`: own AGENTS.md. `fetch` wrapper and hand-written API types.
- `brand-icons.ts`: bundled brand marks (simple-icons, no third-party favicons); `findBrand(...candidates)` looks up by connector key, app slug or name (`normalizeName`, same rule as the API's app catalog keys) and returns `{icon}` or `{color}` (tile with initials); `luminance(hex)` picks text colour on a brand colour.
- `currencies.ts`: `POPULAR_CURRENCIES`, `currencyName(code)` (via `Intl.DisplayNames`), `currencyGroups(codes)` for `SearchableSelect`.
- `date-time.ts`: organization time zone (the browser's until the auth state arrives; none is baked into the build) and `pl-PL` locale; `setAppTimeZone` (called by `AuthGate` from the auth state), `getAppTimeZone`, `formatDateTime(value, options)`.
- `format.ts`: display strings: `formatMoney`, `formatPrice`, `formatWhen`, `formatRelative`, `fullName`, `accountLabel`, `authKindLabel`, `humanize`, `actionOperation(action)` (what a write action does), `parseEmailList`, `slugify`, `emptyToNull`, `amountOf`.
- `json-schema.ts`: reads a connector's `config_schema` (Pydantic JSON Schema) into form fields: `schemaFields(schema, secretFields)`, `initialValues`, `buildPayload`; handles string, number, boolean, enum, string arrays, optional `anyOf` and `$ref`.
- `time-zones.ts`: IANA zones from the browser: `detectTimeZone`, `utcOffset`, `timeZoneLabel`, `timeZoneGroups(detected, current)`.
- `utils.ts`: `cn(...)` (clsx plus tailwind-merge).
- `write-mode.ts`: write mode of an app: `removeVerb(app)` ("Suspend" when `delete_suspends`), `WRITE_MODE_LABEL`, `writeModeHint(mode, what)`.
