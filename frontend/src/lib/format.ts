import { formatDateTime } from "@/lib/date-time";
import type {
  AccountRef,
  ActionOut,
  BillingPeriod,
  MoneyAmount,
  PriceOut,
} from "@/lib/api/types";

/** "1234.50" + "PLN" -> "1 234,50 PLN" (Polish grouping, currency code after). */
export function formatMoney(money: MoneyAmount | null | undefined): string {
  if (!money) return "—";
  const value = Number(money.amount);
  if (Number.isNaN(value)) return `${money.amount} ${money.currency}`;
  const text = new Intl.NumberFormat("pl-PL", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
  return `${text} ${money.currency}`;
}

const PERIOD_SUFFIX: Record<BillingPeriod, string> = { monthly: "/ mo", yearly: "/ yr" };

export function formatPrice(price: PriceOut | null | undefined): string {
  if (!price) return "—";
  return `${formatMoney(price)} ${PERIOD_SUFFIX[price.billing_period]}`;
}

// Numeric, so an English UI shows no Polish month names: "22.11.2026, 18:24".
const WHEN_OPTIONS: Intl.DateTimeFormatOptions = {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
};

/** Date and time in Europe/Warsaw (DD.MM.YYYY, HH:MM), "—" for null. */
export function formatWhen(value: string | null | undefined): string {
  return value ? formatDateTime(value, WHEN_OPTIONS) : "—";
}

/** "just now", "5 min ago", "3 h ago", "2 d ago"; older than a week: the date. */
export function formatRelative(value: string | null | undefined, now: number = Date.now()): string {
  if (!value) return "—";
  const seconds = Math.round((now - Date.parse(value)) / 1000);
  if (Number.isNaN(seconds)) return "—";
  if (seconds < 0) return formatWhen(value);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  if (seconds < 7 * 86400) return `${Math.floor(seconds / 86400)} d ago`;
  return formatDateTime(value, { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** Amount as a number for sorting and bars; 0 for null. */
export function amountOf(money: MoneyAmount | null | undefined): number {
  const value = Number(money?.amount ?? 0);
  return Number.isNaN(value) ? 0 : value;
}

export function fullName(person: { first_name: string; last_name: string }): string {
  return `${person.first_name} ${person.last_name}`.trim();
}

/** Best human label of an account: e-mail, then username, then display name. */
export function accountLabel(account: Pick<AccountRef, "email" | "username" | "display_name">): string {
  return account.email || account.username || account.display_name || "(no identifier)";
}

const AUTH_KIND_LABEL: Record<string, string> = {
  api_token: "API token",
  scim_token: "SCIM token",
  browser_session: "Browser session",
  google_service_account: "Service account",
};

/** How a connector signs in, in words. */
export function authKindLabel(kind: string): string {
  return AUTH_KIND_LABEL[kind] ?? humanize(kind);
}

/** "never_synced" -> "Never synced". */
export function humanize(value: string): string {
  const text = value.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** What the action does, in words: "Create account", "Suspend account", "Delete account (manual task)". */
export function actionOperation(action: Pick<ActionOut, "kind" | "payload" | "suspends">): string {
  if (action.kind === "manual_task") {
    const operation = action.payload.operation;
    return operation ? `${humanize(operation)} (manual task)` : "Manual task";
  }
  if (action.kind === "delete_account" && action.suspends) return "Suspend account";
  return humanize(action.kind);
}

/** Turns "a@x.com, b@x.com\nc@x.com" into a clean, de-duplicated list. */
export function parseEmailList(text: string): string[] {
  const items = text
    .split(/[\s,;]+/)
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
  return [...new Set(items)];
}

/** "Google Workspace!" -> "google-workspace", as the backend expects for slugs. */
export function slugify(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);
}

/** Empty string -> null, so PATCH clears optional fields. */
export function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}
