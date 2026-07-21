// Backend API istemcisi — tüm fetch çağrıları bu dosyada toplanır.
// Kimlik: web oturumu artık HttpOnly `nxs_session` cookie'sinde taşınır
// (bkz. auth-context.tsx) — JS token değerini hiç görmez, `credentials:
// "include"` ile her istekte tarayıcı otomatik gönderir. Admin endpoint'leri
// ayrıca paylaşımlı X-API-Key'i kabul eder (makine-makine / admin olmayan giriş).

import type {
  AccountUsage, AdminUserList, BillingConfig, CheckoutResponse, NewsPage, RelatedResponse,
  SearchResult, Sponsor, TrendingResponse, UsageRow, User,
} from "./types";

export const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Admin çağrıları için kimlik: admin kullanıcı oturumu (cookie, otomatik) VEYA paylaşımlı anahtar. */
export interface AdminCreds {
  apiKey?: string | null;
}

function adminHeaders(creds: AdminCreds): HeadersInit {
  return creds.apiKey ? { "X-API-Key": creds.apiKey } : {};
}

/** `req()`'in fırlattığı hata — `status` alanı sayesinde çağıran taraf (örn. 429 rate limit) özel ele alabilir. */
export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * FastAPI'nin `detail` alanı her zaman string değildir — Pydantic doğrulama
 * hatalarında (422) `[{type, loc, msg, ...}, ...]` dizisi döner. Bunu doğrudan
 * `Error` mesajına vermek `String([{...}])` → "[object Object]" ile sonuçlanır
 * (Array.prototype.toString her elemanı ToString'e çevirip virgülle birleştirir,
 * objenin varsayılan toString'i de "[object Object]"tir). Her iki şekli de
 * okunabilir bir stringe indirger.
 */
function extractErrorMessage(err: unknown, fallback: string): string {
  const detail = (err as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail.map((e) => (typeof e === "string" ? e : (e as { msg?: string })?.msg)).filter(Boolean);
    if (msgs.length) return msgs.join(" ");
  }
  if (detail && typeof detail === "object") {
    const msg = (detail as { msg?: string }).msg;
    if (msg) return msg;
  }
  return fallback;
}

/** Ortak fetch sarmalayıcı: `nxs_session` cookie'sini taşır, hata gövdesindeki `detail`'i Error'a çevirir. */
async function req<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(extractErrorMessage(err, `HTTP ${res.status}`), res.status);
  }
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function apiRegister(email: string, password: string, name: string, language: string) {
  return req<{ user: User }>(`${BASE}/auth/register`, {
    method: "POST",
    body: JSON.stringify({ email, password, name, language }),
  });
}

export async function apiLogin(email: string, password: string) {
  return req<{ user: User }>(`${BASE}/auth/login`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function apiLogout() {
  await fetch(`${BASE}/auth/logout`, { method: "POST", credentials: "include" });
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

export async function apiResendVerification(language: string) {
  return req<{ message: string }>(`${BASE}/auth/resend-verification`, {
    method: "POST",
    body: JSON.stringify({ language }),
  });
}

export async function apiVerifyEmail(token: string) {
  return req<{ message: string }>(`${BASE}/auth/verify-email`, {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

/** Aktif oturumun güncel kullanıcı bilgisi (tier/is_admin tazelemek için) — cookie ile kimliklenir. */
export async function fetchMe(): Promise<User> {
  return req<User>(`${BASE}/auth/me`);
}

// ── News ──────────────────────────────────────────────────────────────────────

export async function fetchNews(params: {
  limit?: number;
  cursor?: number | null;
  source?: string;
  sentiment?: string;
  topic?: string;
  min_quality?: number;
}): Promise<NewsPage> {
  const p = new URLSearchParams();
  if (params.limit) p.set("limit", String(params.limit));
  if (params.cursor) p.set("cursor", String(params.cursor));
  if (params.source) p.set("source", params.source);
  if (params.sentiment) p.set("sentiment", params.sentiment);
  if (params.topic) p.set("topic", params.topic);
  if (params.min_quality != null) p.set("min_quality", String(params.min_quality));
  return req<NewsPage>(`${BASE}/api/v1/news?${p}`);
}

export async function searchNews(query: string, n_results = 10): Promise<SearchResult[]> {
  return req<SearchResult[]>(`${BASE}/api/v1/news/search`, {
    method: "POST",
    body: JSON.stringify({ query, n_results }),
  });
}

/** Landing sayfası demosu için — tamamen public, kota/oturum gerektirmeyen `/news/search`. */
export async function searchNewsPublic(query: string, n_results = 5): Promise<SearchResult[]> {
  return req<SearchResult[]>(`${BASE}/news/search`, {
    method: "POST",
    body: JSON.stringify({ query, n_results }),
  });
}

export async function fetchTrending(hours = 6, limit = 10): Promise<TrendingResponse> {
  return req<TrendingResponse>(`${BASE}/api/v1/news/trending?hours=${hours}&limit=${limit}`);
}

export async function fetchRelated(id: number): Promise<RelatedResponse> {
  return req<RelatedResponse>(`${BASE}/api/v1/news/${id}/related`);
}

export async function fetchSources(): Promise<string[]> {
  return req<string[]>(`${BASE}/api/v1/news/sources`);
}

// ── Account (v1.11 self-service) ──────────────────────────────────────────────

export async function fetchMyUsage(days = 7): Promise<AccountUsage> {
  return req<AccountUsage>(`${BASE}/account/usage?days=${days}`);
}

export async function generateApiKey(): Promise<{ api_key: string }> {
  return req<{ api_key: string }>(`${BASE}/account/api-key`, { method: "POST" });
}

export async function revokeApiKey(): Promise<void> {
  await req(`${BASE}/account/api-key`, { method: "DELETE" });
}

export async function fetchApiKey(): Promise<{ api_key: string | null; has_api_key: boolean }> {
  return req(`${BASE}/account/api-key`);
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function fetchUsage(creds: AdminCreds, userId?: number, days = 30): Promise<UsageRow[]> {
  const p = new URLSearchParams({ days: String(days) });
  if (userId) p.set("user_id", String(userId));
  return req<UsageRow[]>(`${BASE}/admin/usage?${p}`, { headers: adminHeaders(creds) });
}

/** Müşteri/kullanıcı listesi — tier, aktiflik, `is_paying` (gerçek Stripe müşterisi mi, dev-mode mi). */
export async function fetchUsers(creds: AdminCreds, limit = 50, offset = 0, tier?: string): Promise<AdminUserList> {
  const p = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (tier) p.set("tier", tier);
  return req<AdminUserList>(`${BASE}/admin/users?${p}`, { headers: adminHeaders(creds) });
}

/** Başka bir kullanıcının rolünü değiştirir — sadece admin (moderator yeterli değil). */
export async function updateUserRole(creds: AdminCreds, userId: number, role: string): Promise<{ id: number; role: string }> {
  return req(`${BASE}/admin/users/${userId}/role`, {
    method: "PATCH",
    headers: adminHeaders(creds),
    body: JSON.stringify({ role }),
  });
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

/** Süresi geçmemiş pasif bir sponsoru yeniden aktifleştirir (diğer aktifler otomatik pasife alınır). */
export async function activateSponsor(creds: AdminCreds, id: number): Promise<Sponsor> {
  return req<Sponsor>(`${BASE}/admin/sponsors/${id}/activate`, { method: "POST", headers: adminHeaders(creds) });
}

/** Sponsoru kalıcı olarak siler — geri alınamaz. */
export async function deleteSponsorPermanently(creds: AdminCreds, id: number): Promise<void> {
  await req(`${BASE}/admin/sponsors/${id}/permanent`, { method: "DELETE", headers: adminHeaders(creds) });
}

// ── Billing ───────────────────────────────────────────────────────────────────

export async function fetchBillingConfig(): Promise<BillingConfig> {
  return req<BillingConfig>(`${BASE}/billing/config`);
}

export async function createCheckout(tier: string, successUrl: string, cancelUrl: string): Promise<CheckoutResponse> {
  return req<CheckoutResponse>(`${BASE}/billing/checkout`, {
    method: "POST",
    body: JSON.stringify({ tier, success_url: successUrl, cancel_url: cancelUrl }),
  });
}

export async function getBillingPortal() {
  return req<{ url: string }>(`${BASE}/billing/portal`);
}

/** Dev modda aboneliği iptal simülasyonu — tier'ı Free'ye çeker. */
export async function devDowngrade(): Promise<{ tier: string }> {
  return req<{ tier: string }>(`${BASE}/billing/dev/downgrade`, { method: "POST" });
}
