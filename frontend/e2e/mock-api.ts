// Backend'siz UI denetimi için API taklidi. Veri BİLİNÇLİ olarak kötü senaryo:
// uzun Türkçe başlıklar, uzun entity adları, boşluksuz uzun kelime — taşma/kırpma
// hatalarını gerçek içerikten ÖNCE yakalamak için.
import type { Page } from "@playwright/test";

const LONG_TITLE =
  "Cumhurbaşkanlığı Hükümet Sistemi kapsamında yeniden yapılandırılan uluslararası koordinasyon kurulunun olağanüstü toplantısı sona erdi";

const article = (id: number) => ({
  id,
  title: id % 3 === 0 ? LONG_TITLE : `Haber başlığı numara ${id}: kısa bir örnek`,
  source: id % 2 ? "Anadolu Ajansı Ekonomi" : "BBC Technology",
  url: `https://example.com/haber/${id}`,
  content: "İçerik",
  summary:
    "Bu özet, kartın taşma davranışını sınamak için kasten uzun tutulmuştur ve https://cok-uzun-bir-bosluksuz-baglanti-ornegi.example.com/yol/yol/yol/yol/yol içerir.",
  sentiment_label: (["Positive", "Negative", "Neutral"] as const)[id % 3],
  sentiment_score: 0.4,
  topic: ["Technology", "Sports", "Economy", "Politics"][id % 4],
  entities: {
    persons: ["Recep Tayyip Erdoğan", "Abdulkadiroğlu-Karabekiroğlu Uzunisimli"],
    organizations: ["Birleşmiş Milletler Güvenlik Konseyi Daimi Üyeleri"],
    locations: ["İstanbul", "Ankara"],
  },
  quality_score: 0.8,
  credibility_score: 0.7,
  corroboration_count: 3,
  trust_score: 82,
  trust_breakdown: { quality: 28, credibility: 32, corroboration: 18 },
  created_at: new Date(Date.now() - id * 3_600_000).toISOString(),
  published_at: new Date(Date.now() - id * 3_600_000).toISOString(),
});

export const USER = {
  id: 1, email: "uzun.bir.kullanici.adresi.ornegi@ornek-alan-adi.com.tr", name: "Uzun Adlı Örnek Kullanıcı",
  tier: "enterprise", role: "owner", is_admin: true, is_moderator: true, is_owner: true,
  effective_tier: "enterprise", email_verified: true, created_at: "2026-07-01T00:00:00Z",
};

function respond(path: string, method: string, loggedIn: boolean): { status: number; body: unknown } {
  if (path === "/auth/me") return loggedIn ? { status: 200, body: USER } : { status: 401, body: { detail: "no" } };
  if (path === "/api/v1/news") return { status: 200, body: { items: Array.from({ length: 20 }, (_, i) => article(i + 1)), next_cursor: "1_1", count: 20 } };
  if (path === "/api/v1/news/trending") return { status: 200, body: { hours: 6, entities: ["Erdoğan", "Galatasaray", "Merkez Bankası", "Yapay Zeka", "Birleşmiş Milletler", "Kripto"].map((name, i) => ({ name, count: 12 - i, type: "person", example_titles: [LONG_TITLE] })) } };
  if (path === "/api/v1/news/sources") return { status: 200, body: ["TRT Haber", "BBC Türkçe", "Anadolu Ajansı Ekonomi", "BBC Technology", "The Verge"] };
  if (path.startsWith("/api/v1/news/search") || path === "/news/search") return { status: 200, body: Array.from({ length: 8 }, (_, i) => ({ ...article(i + 1), score: 0.9 - i / 20 })) };
  if (path.endsWith("/related")) return { status: 200, body: { article_id: 1, related: [{ id: 2, title: LONG_TITLE, source: "TRT Haber", url: "https://e.com", common_entities: ["İstanbul Büyükşehir Belediyesi"], overlap_score: 0.5 }] } };
  if (path.endsWith("/sources")) return { status: 200, body: { article_id: 1, sources: [{ id: 2, title: LONG_TITLE, source: "TRT Haber", url: "https://e.com", score: 0.9, trust_score: 80 }] } };
  if (path === "/api/v1/news/ask") return { status: 200, body: { answer: "Örnek cevap. ".repeat(30), coverage: "full", corroboration_level: "multi_source", sources: [{ index: 1, title: LONG_TITLE, source: "TRT Haber", url: "https://e.com" }], suggest_alert: true } };
  if (path === "/account/usage") return { status: 200, body: { tier: "enterprise", daily_limit: null, used_today: 12, remaining_today: null, days: 7, total_requests: 80, by_endpoint: [{ user_id: 1, endpoint: "/api/v1/news/search-cok-uzun-endpoint-adi", count: 10, avg_ms: 30 }], has_api_key: false } };
  if (path === "/account/api-key") return { status: 200, body: { api_key: null, has_api_key: false } };
  if (path === "/account/saved") return { status: 200, body: [article(1), article(2)] };
  if (path === "/account/newsletter") return { status: 200, body: { subscribed: false, email: USER.email, frequency: "daily", topics: [], sources: [], keywords: [], language: "TR" } };
  if (path === "/billing/config") return { status: 200, body: { dev_mode: true, stripe_configured: false } };
  if (path === "/market/ticker") return { status: 200, body: { bist100: { value: 10000, change_pct: 1.2 }, usd_try: { value: 40, change_pct: -0.3 }, eur_try: { value: 46, change_pct: 0.1 }, gold_gram_try: { value: 4200, change_pct: 0.5 }, as_of: new Date().toISOString(), stale: false } };
  if (path === "/admin/users") return { status: 200, body: { total: 2, items: [{ id: 1, email: USER.email, name: USER.name, tier: "enterprise", is_active: true, email_verified: true, role: "owner", is_paying: false, created_at: "2026-07-01T00:00:00Z" }] } };
  if (path.startsWith("/admin/")) return { status: 200, body: [] };
  if (path === "/billing/dev/downgrade" || method !== "GET") return { status: 200, body: { success: true, message: "ok" } };
  return { status: 200, body: {} };
}

/** Tüm backend çağrılarını (localhost:8000) yakalar; RSS ve WebSocket sessiz kalır. */
export async function mockApi(page: Page, loggedIn: boolean) {
  await page.route(/localhost:8000/, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith(".xml")) {
      return route.fulfill({ status: 200, contentType: "application/rss+xml", body: `<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>${Array.from({ length: 6 }, (_, i) => `<item><title>${LONG_TITLE} ${i}</title><link>https://e.com/${i}</link><pubDate>${new Date().toUTCString()}</pubDate></item>`).join("")}</channel></rss>` });
    }
    const { status, body } = respond(url.pathname.replace(/\/$/, "") || "/", route.request().method(), loggedIn);
    return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  });
}
