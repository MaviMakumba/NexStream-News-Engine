// Backend API istemcisi — tüm fetch çağrıları bu dosyada toplanır.
// Kimlik header'ları:
//   X-Session-Token : web oturumu (login sonrası)
//   X-API-Key       : paylaşımlı admin anahtarı (makine-makine)
// Admin endpoint'leri v1.11'den itibaren her ikisini de kabul eder; admin
// kullanıcılar (is_admin) session token ile anahtar girmeden erişir.

import type {
  AccountUsage, BillingConfig, CheckoutResponse, NewsPage, RelatedResponse,
  SearchResult, Sponsor, TrendingResponse, UsageRow, User,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Admin çağrıları için kimlik: session token (admin kullanıcı) VEYA paylaşımlı anahtar. */
export interface AdminCreds {
  token?: string | null;
  apiKey?: string | null;
}

function authHeaders(token?: string | null): HeadersInit {
  return token ? { "X-Session-Token": token } : {};
}

function adminHeaders(creds: AdminCreds): HeadersInit {
  const h: Record<string, string> = {};
  if (creds.token) h["X-Session-Token"] = creds.token;
  if (creds.apiKey) h["X-API-Key"] = creds.apiKey;
  return h;
}

/** Ortak fetch sarmalayıcı: hata gövdesindeki `detail` alanını Error mesajına taşır. */
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
  return req<{ token: string; user: User }>(`${BASE}/auth/register`, {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

export async function apiLogin(email: string, password: string) {
  return req<{ token: string; user: User }>(`${BASE}/auth/login`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function apiLogout(token: string) {
  await fetch(`${BASE}/auth/logout`, { method: "POST", headers: authHeaders(token) });
}

export async function apiForgotPassword(email: string, language: string) {
  return req<{ message: string }>(`${BASE}/auth/forgot-password`, {
    method: "POST",
    body: JSON.stringify({ email, language }),
  });
}

export async function apiResetPassword(token: string, password: string) {
  return req<{ message: string }>(`${BASE}/auth/reset-password`, {
    method: "POST",
    body: JSON.stringify({ token, password }),
  });
}

/** Aktif oturumun güncel kullanıcı bilgisi (tier/is_admin tazelemek için). */
export async function fetchMe(token: string): Promise<User> {
  return req<User>(`${BASE}/auth/me`, { headers: authHeaders(token) });
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

// ── Account (v1.11 self-service) ──────────────────────────────────────────────

export async function fetchMyUsage(token: string, days = 7): Promise<AccountUsage> {
  return req<AccountUsage>(`${BASE}/account/usage?days=${days}`, { headers: authHeaders(token) });
}

export async function generateApiKey(token: string): Promise<{ api_key: string }> {
  return req<{ api_key: string }>(`${BASE}/account/api-key`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function revokeApiKey(token: string): Promise<void> {
  await req(`${BASE}/account/api-key`, { method: "DELETE", headers: authHeaders(token) });
}

export async function fetchApiKey(token: string): Promise<{ api_key: string | null; has_api_key: boolean }> {
  return req(`${BASE}/account/api-key`, { headers: authHeaders(token) });
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function fetchUsage(creds: AdminCreds, userId?: number, days = 30): Promise<UsageRow[]> {
  const p = new URLSearchParams({ days: String(days) });
  if (userId) p.set("user_id", String(userId));
  return req<UsageRow[]>(`${BASE}/admin/usage?${p}`, { headers: adminHeaders(creds) });
}

export async function fetchSponsors(creds: AdminCreds): Promise<Sponsor[]> {
  return req<Sponsor[]>(`${BASE}/admin/sponsors`, { headers: adminHeaders(creds) });
}

export async function createSponsor(creds: AdminCreds, data: {
  name: string; url: string; message: string; active_from: string; active_until: string;
}): Promise<Sponsor> {
  return req<Sponsor>(`${BASE}/admin/sponsors`, {
    method: "POST",
    headers: adminHeaders(creds),
    body: JSON.stringify(data),
  });
}

export async function deactivateSponsor(creds: AdminCreds, id: number): Promise<void> {
  await req(`${BASE}/admin/sponsors/${id}`, { method: "DELETE", headers: adminHeaders(creds) });
}

// ── Billing ───────────────────────────────────────────────────────────────────

export async function fetchBillingConfig(): Promise<BillingConfig> {
  return req<BillingConfig>(`${BASE}/billing/config`);
}

export async function createCheckout(token: string, tier: string, successUrl: string, cancelUrl: string): Promise<CheckoutResponse> {
  return req<CheckoutResponse>(`${BASE}/billing/checkout`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ tier, success_url: successUrl, cancel_url: cancelUrl }),
  });
}

export async function getBillingPortal(token: string) {
  return req<{ url: string }>(`${BASE}/billing/portal`, { headers: authHeaders(token) });
}

/** Dev modda aboneliği iptal simülasyonu — tier'ı Free'ye çeker. */
export async function devDowngrade(token: string): Promise<{ tier: string }> {
  return req<{ tier: string }>(`${BASE}/billing/dev/downgrade`, {
    method: "POST",
    headers: authHeaders(token),
  });
}
