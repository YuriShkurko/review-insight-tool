import { trailEvent } from "./debugTrail";

const CONFIGURED_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const FRIENDLY_MESSAGES: Record<number, string> = {
  401: "Your session has expired. Please sign in again.",
  403: "You don't have permission to do that.",
  404: "The requested resource was not found.",
  409: "This resource already exists.",
  422: "Please check your input and try again.",
};

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

let onUnauthorized: (() => void) | null = null;

export function setOnUnauthorized(cb: () => void) {
  onUnauthorized = cb;
}

export function getApiBaseUrl(): string {
  if (typeof window === "undefined") return CONFIGURED_BASE_URL;

  try {
    const configured = new URL(CONFIGURED_BASE_URL);
    const pageHost = window.location.hostname;
    const configuredHost = configured.hostname;
    const isConfiguredLocalhost = configuredHost === "localhost" || configuredHost === "127.0.0.1";
    const isPageLocalhost = pageHost === "localhost" || pageHost === "127.0.0.1";

    if (isConfiguredLocalhost && !isPageLocalhost) {
      configured.hostname = pageHost;
      return configured.toString().replace(/\/$/, "");
    }
  } catch {
    return CONFIGURED_BASE_URL;
  }

  return CONFIGURED_BASE_URL;
}

export function apiStreamFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(`${getApiBaseUrl()}/api${path}`, { ...options, headers });
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const method = (options.method ?? "GET").toUpperCase();
  const baseUrl = getApiBaseUrl();
  trailEvent("api:start", { method, path, base_url: baseUrl });

  let res: Response;
  try {
    res = await fetch(`${baseUrl}/api${path}`, { ...options, headers });
  } catch {
    trailEvent("api:fail", {
      method,
      path,
      base_url: baseUrl,
      status: 0,
      detail: "Network error",
    });
    throw new ApiError(0, "Network error. Please check your connection.");
  }

  if (!res.ok) {
    if (res.status === 401 && onUnauthorized) {
      onUnauthorized();
    }
    const body = await res.json().catch(() => ({}));
    const detail = body.detail || FRIENDLY_MESSAGES[res.status] || "Something went wrong.";
    trailEvent("api:fail", { method, path, base_url: baseUrl, status: res.status, detail });
    throw new ApiError(res.status, detail);
  }

  const traceId = res.headers.get("x-trace-id") ?? undefined;
  trailEvent("api:ok", {
    method,
    path,
    base_url: baseUrl,
    status: res.status,
    trace_id: traceId,
  });
  if (res.status === 204) return undefined as T;
  return res.json();
}
