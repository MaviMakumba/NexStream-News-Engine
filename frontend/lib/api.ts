import type { Article, NewsPage, SearchResult, TrendingResponse, RelatedResponse, UsageRow, Sponsor } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function authHeaders(token?: string | null): HeadersInit {
  return token ? { "X-Session-Token": token } : {};
}

function adminHeaders(apiKey: string): HeadersInit {
  return { "X-API-Key": apiKey };
}

async function req<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, { ...options, headers: { "Content-Type": "application/json", ...options?.headers } });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function apiRegister(email: string, password: string, name: string) {
  return req<{ token: string; user: import("./types").User }>(`${BASE}/auth/register`, {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

export async function apiLogin(email: string, password: string) {
  return req<{ token: string; user: import("./types").User }>(`${BASE}/auth/login`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function apiLogout(token: string) {
  await fetch(`${BASE}/auth/logout`, { method: "POST", headers: authHeaders(token) });
}

// ── News ──────────────────────────────────────────────────────────────────────

export async function fetchNews(params: {
  limit?: number;
  cursor?: number | null;
  source?: string;
  sentiment?: string;
  topic?: string;
  min_quality?: number;
}, token?: string | null): Promise<NewsPage> {
  const p = new URLSearchParams();
  if (params.limit) p.set("limit", String(params.limit));
  if (params.cursor) p.set("cursor", String(params.cursor));
  if (params.source) p.set("source", params.source);
  if (params.sentiment) p.set("sentiment", params.sentiment);
  if (params.topic) p.set("topic", params.topic);
  if (params.min_quality != null) p.set("min_quality", String(params.min_quality));
  return req<NewsPage>(`${BASE}/api/v1/news?${p}`, { headers: authHeaders(token) });
}

export async function searchNews(query: string, n_results = 10, token?: string | null): Promise<SearchResult[]> {
  return req<SearchResult[]>(`${BASE}/api/v1/news/search`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ query, n_results }),
  });
}

export async function fetchTrending(hours = 6, limit = 10, token?: string | null): Promise<TrendingResponse> {
  return req<TrendingResponse>(`${BASE}/api/v1/news/trending?hours=${hours}&limit=${limit}`, {
    headers: authHeaders(token),
  });
}

export async function fetchRelated(id: number, token?: string | null): Promise<RelatedResponse> {
  return req<RelatedResponse>(`${BASE}/api/v1/news/${id}/related`, {
    headers: authHeaders(token),
  });
}

export async function fetchSources(): Promise<string[]> {
  return req<string[]>(`${BASE}/api/v1/news/sources`);
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function fetchUsage(apiKey: string, userId?: number, days = 30): Promise<UsageRow[]> {
  const p = new URLSearchParams({ days: String(days) });
  if (userId) p.set("user_id", String(userId));
  return req<UsageRow[]>(`${BASE}/admin/usage?${p}`, { headers: adminHeaders(apiKey) });
}

export async function fetchSponsors(apiKey: string): Promise<Sponsor[]> {
  return req<Sponsor[]>(`${BASE}/admin/sponsors`, { headers: adminHeaders(apiKey) });
}

export async function createSponsor(apiKey: string, data: {
  name: string; url: string; message: string; active_from: string; active_until: string;
}): Promise<Sponsor> {
  return req<Sponsor>(`${BASE}/admin/sponsors`, {
    method: "POST",
    headers: adminHeaders(apiKey),
    body: JSON.stringify(data),
  });
}

export async function deactivateSponsor(apiKey: string, id: number): Promise<void> {
  await req(`${BASE}/admin/sponsors/${id}`, { method: "DELETE", headers: adminHeaders(apiKey) });
}

// ── Billing ───────────────────────────────────────────────────────────────────

export async function createCheckout(token: string, tier: string, successUrl: string, cancelUrl: string) {
  return req<{ url: string }>(`${BASE}/billing/checkout`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ tier, success_url: successUrl, cancel_url: cancelUrl }),
  });
}

export async function getBillingPortal(token: string) {
  return req<{ url: string }>(`${BASE}/billing/portal`, { headers: authHeaders(token) });
}
