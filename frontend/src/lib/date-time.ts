const DEFAULT_LOCALE = "pl-PL";

/** The browser's own zone; UTC on the server and where the browser does not say. */
function browserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

// Until the auth state arrives: this browser's zone (no zone is baked into the build, so one image
// fits every installation). Then the organization's zone (AuthGate calls setAppTimeZone first).
let appTimeZone = browserTimeZone();

export function setAppTimeZone(zone: string | null | undefined): void {
  if (zone) appTimeZone = zone;
}

export function getAppTimeZone(): string {
  return appTimeZone;
}

const DEFAULT_DATE_TIME_OPTIONS: Intl.DateTimeFormatOptions = {
  dateStyle: "medium",
  timeStyle: "short",
};

export function formatDateTime(
  value: Date | string | number,
  options: Intl.DateTimeFormatOptions = DEFAULT_DATE_TIME_OPTIONS,
): string {
  return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    ...options,
    timeZone: appTimeZone,
  }).format(new Date(value));
}
