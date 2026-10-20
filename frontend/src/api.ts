import type { IncidentDetail, IncidentPage, Session, Stats, Severity, Status } from "./types";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

function csrfCookie(): string {
  const entry = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith("csrftoken="));
  return entry ? decodeURIComponent(entry.slice("csrftoken=".length)) : "";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method?.toUpperCase() ?? "GET";
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body != null) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-CSRFToken", csrfCookie());
  }
  const response = await fetch(path, {
    ...init,
    headers,
    credentials: "same-origin",
  });
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError("The server returned an unexpected response.", response.status);
  }
  if (!response.ok) {
    const detail = (payload as { detail?: unknown } | null)?.detail;
    throw new ApiError(typeof detail === "string" ? detail : "Request failed.", response.status);
  }
  return payload as T;
}

export const api = {
  session: () => request<Session>("/api/v1/session/"),
  login: (username: string, password: string) =>
    request<Session>("/api/v1/login/", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<Session>("/api/v1/logout/", { method: "POST" }),
  list: (filters: { status?: Status; severity?: Severity; q?: string; page?: number }) => {
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.severity) params.set("severity", filters.severity);
    if (filters.q) params.set("q", filters.q);
    if (filters.page && filters.page > 1) params.set("page", String(filters.page));
    return request<IncidentPage>(`/api/v1/incidents/?${params.toString()}`);
  },
  stats: () => request<Stats>("/api/v1/incidents/stats/"),
  detail: (id: string) => request<IncidentDetail>(`/api/v1/incidents/${encodeURIComponent(id)}/`),
  action: (id: string, action: "acknowledge" | "resolve") =>
    request<IncidentDetail>(`/api/v1/incidents/${encodeURIComponent(id)}/${action}/`, { method: "POST" }),
};
