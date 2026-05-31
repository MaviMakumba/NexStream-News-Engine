export type Tier = "free" | "pro" | "enterprise";

export interface User {
  id: number;
  email: string;
  name: string;
  tier: Tier;
  created_at?: string;
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
  entity: string;
  count: number;
  articles: number[];
}

export interface TrendingResponse {
  hours: number;
  entities: TrendingEntity[];
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

export interface UsageRow {
  user_id: number | null;
  endpoint: string;
  count: number;
  avg_ms: number;
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
