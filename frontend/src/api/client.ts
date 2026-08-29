import { API_BASE_URL } from "../config";

// ---------------------------------------------------------------------------
// Token helpers
// ---------------------------------------------------------------------------

const TOKEN_KEY = "ai_director_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// API Error
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

// ---------------------------------------------------------------------------
// Generic request helper
// ---------------------------------------------------------------------------

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, headers: extraHeaders = {} } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extraHeaders,
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Token ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body != null ? JSON.stringify(body) : undefined,
  });

  const text = await response.text();
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    raw = text;
  }

  if (!response.ok) {
    throw new ApiError(response.status, text, raw);
  }

  // Backend wraps success responses: { success: true, data: <payload> }
  // Unwrap the envelope so callers receive the payload directly.
  if (
    typeof raw === "object" &&
    raw !== null &&
    "success" in raw &&
    (raw as Record<string, unknown>).success === true &&
    "data" in raw
  ) {
    return (raw as Record<string, unknown>).data as T;
  }

  return raw as T;
}

// ---------------------------------------------------------------------------
// Typed API helpers
// ---------------------------------------------------------------------------

export const api = {
  get: <T = unknown>(path: string) => apiRequest<T>(path),
  post: <T = unknown>(path: string, body?: unknown) =>
    apiRequest<T>(path, { method: "POST", body }),
  put: <T = unknown>(path: string, body?: unknown) =>
    apiRequest<T>(path, { method: "PUT", body }),
  patch: <T = unknown>(path: string, body?: unknown) =>
    apiRequest<T>(path, { method: "PATCH", body }),
};
