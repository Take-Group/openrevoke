// Thin fetch wrapper for the Open Revoke API.
//
// The browser always calls the same origin (`/api/...`). Next.js rewrites
// `/api/:path*` to `${API_PROXY_TARGET}/api/:path*` (next.config.ts), so the
// panel needs no CORS and no public API URL.

/**
 * Sent with every request. The API refuses POST, PATCH and DELETE without it:
 * another site cannot add a custom header without a CORS preflight, which the
 * API refuses, so it cannot use the session cookie (CSRF).
 */
export const CLIENT_HEADER = "X-Open-Revoke-Client";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  /** No session or it expired (HTTP 401). The auth gate sends the user to sign in. */
  get unauthorized(): boolean {
    return this.status === 401;
  }

  /** The endpoint belongs to a later build stage (HTTP 501). */
  get notImplemented(): boolean {
    return this.status === 501;
  }
}

export function isNotImplemented(error: unknown): boolean {
  return error instanceof ApiError && error.notImplemented;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.notImplemented) return "Not available yet: the backend does not implement this endpoint.";
    return error.detail;
  }
  if (error instanceof Error) return error.message;
  return "Unknown error";
}

type QueryValue = string | number | boolean | null | undefined | readonly (string | number)[];
export type QueryParams = Record<string, QueryValue>;

/** Builds `?a=1&b=x&status=a&status=b`, skipping empty values. */
export function buildQuery(params?: QueryParams): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const item of value) search.append(key, String(item));
    } else {
      search.append(key, String(value));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

function detailFromBody(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // FastAPI 422: a list of {loc, msg}.
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          const loc = Array.isArray(item?.loc) ? item.loc.filter((p: unknown) => p !== "body").join(".") : "";
          return loc ? `${loc}: ${item?.msg}` : String(item?.msg ?? "");
        })
        .join("; ");
    }
  }
  return fallback;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const headers = new Headers(init?.headers);
  headers.set(CLIENT_HEADER, "panel");
  if (init?.body && !isForm && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(0, "Cannot reach the API. Is the backend running?");
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, detailFromBody(body, `Request failed with HTTP ${response.status}`));
  }
  return body as T;
}

export function apiGet<T>(path: string, params?: QueryParams): Promise<T> {
  return apiFetch<T>(`${path}${buildQuery(params)}`);
}

export function apiSend<T>(method: "POST" | "PUT" | "PATCH" | "DELETE", path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method,
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
  });
}
