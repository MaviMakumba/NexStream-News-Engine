// Backend API yanıtlarının TypeScript karşılıkları.
// Alan adları Pydantic şemalarıyla birebir aynıdır (snake_case korunur).

export type Tier = "free" | "pro" | "enterprise";
export type Role = "user" | "moderator" | "admin" | "owner";

export interface User {
  id: number;
  email: string;
  name: string;
  tier: Tier;
  role?: Role;                 // v1.13: yetki hiyerarşisi (backend hesaplar, ADMIN_EMAILS dahil)
  is_admin?: boolean;          // geriye dönük uyumluluk — role === "admin" ile aynı
  is_moderator?: boolean;      // role moderator VEYA admin VEYA owner
  is_owner?: boolean;          // v2.1: OWNER_EMAILS bootstrap veya role="owner"
  effective_tier?: Tier;       // v2.1: owner için her zaman "enterprise", diğerlerinde tier ile aynı
  email_verified?: boolean;    // v1.15: Free tier erişimini kısıtlamaz, sadece ücretli yükseltme ister
  created_at?: string;
}

// v1.11: /account/usage — kullanıcının kendi kota & kullanım özeti
export interface AccountUsage {
  tier: Tier;
  daily_limit: number | null;  // null = sınırsız (Enterprise)
  used_today: number;
  remaining_today: number | null;
  days: number;
  total_requests: number;
  by_endpoint: UsageRow[];
  has_api_key: boolean;
}

// v1.11: /billing/config — frontend'in ödeme akışını seçmesi için
export interface BillingConfig {
  dev_mode: boolean;
  stripe_configured: boolean;
}

// /billing/checkout yanıtı — dev modda yönlendirme yerine anında yükseltme olur
export interface CheckoutResponse {
  url: string;
  dev_mode?: boolean;
  tier?: Tier;
}

export interface Article {
  id: number;
  title: string;
  source: string;
  url: string;
  content: string;
  summary?: string;
  sentiment_label?: "Positive" | "Negative" | "Neutral";
  sentiment_score?: number;
  topic?: string;
  entities?: {
    persons: string[];
    organizations: string[];
    locations: string[];
  };
  quality_score?: number;
  credibility_score?: number;
  corroboration_count?: number;
  created_at: string;
  published_at?: string;
}

export interface NewsPage {
  items: Article[];
  next_cursor: number | null;
  count: number;
}

export interface SearchResult {
  id: number;
  title: string;
  source: string;
  url: string;
  summary?: string;
  sentiment_label?: string;
  topic?: string;
  score: number;
  created_at: string;
}

export interface TrendingEntity {
  name: string;
  count: number;
  type?: string;
  example_titles?: string[];
}

export interface TrendingResponse {
  hours: number;
  entities: TrendingEntity[];
}

export interface MarketQuote {
  value: number;
  change_pct: number;
}

export interface MarketSnapshot {
  bist100: MarketQuote;
  usd_try: MarketQuote;
  eur_try: MarketQuote;
  gold_gram_try: MarketQuote;
  as_of: string;
  stale: boolean;
}

export interface RelatedArticle {
  id: number;
  title: string;
  source: string;
  url: string;
  common_entities: string[];
  overlap_score: number;
}

export interface RelatedResponse {
  article_id: number;
  related: RelatedArticle[];
}

// v2.2 — story cluster ("bu haberi kim nasıl anlatıyor"). related'dan farkı:
// entity kesişimi değil semantik vektör benzerliği, tier gating yok (herkese açık).
export interface StorySource {
  id: number;
  title: string;
  source: string;
  url: string;
  score: number;
}

export interface StoryClusterResponse {
  article_id: number;
  sources: StorySource[];
}

export interface UsageRow {
  user_id: number | null;
  endpoint: string;
  count: number;
  avg_ms: number;
}

export interface AdminUser {
  id: number;
  email: string;
  name: string;
  tier: string;
  is_active: boolean;
  email_verified: boolean;
  role: Role;
  is_paying: boolean;
  created_at: string;
}

export interface AdminUserList {
  total: number;
  items: AdminUser[];
}

export interface Sponsor {
  id: number;
  name: string;
  url: string;
  message: string;
  active_from: string;
  active_until: string;
  is_active: boolean;
}

// v2.6 — RAG soru-cevap (roadmap #13).
export interface AskMessage {
  role: "user" | "assistant";
  content: string;
}

export interface RagSource {
  index: number;
  title: string;
  source: string;
  url: string;
}

export interface RagAnswerResponse {
  answer: string;
  coverage: "full" | "partial" | "none";
  corroboration_level: "single_source" | "multi_source" | "none";
  sources: RagSource[];
  suggest_alert: boolean;
}
