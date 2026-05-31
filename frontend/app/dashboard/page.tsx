"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { fetchNews, fetchTrending, fetchSources } from "@/lib/api";
import type { Article, TrendingEntity } from "@/lib/types";
import { NewsCard } from "@/components/NewsCard";
import { TrendingPills } from "@/components/TrendingPills";
import { TOPIC_LABELS, SENTIMENT_LABELS, UI } from "@/lib/i18n";

const TOPIC_VALUES    = ["", "Technology", "Sports", "Economy", "Politics", "Health", "Culture", "World", "Other"];
const SENTIMENT_VALUES = ["", "Positive", "Negative", "Neutral"];

export default function DashboardPage() {
  const { token } = useAuth();
  const { lang } = useSettings();
  const router = useRouter();
  const t = UI[lang];

  const [articles,        setArticles]        = useState<Article[]>([]);
  const [trending,        setTrending]        = useState<TrendingEntity[]>([]);
  const [trendingLoaded,  setTrendingLoaded]  = useState(false);
  const [sources,         setSources]         = useState<string[]>([]);
  const [loading,         setLoading]         = useState(true);
  const [cursor,          setCursor]          = useState<number | null>(null);
  const [hasMore,         setHasMore]         = useState(true);
  const [sentiment,       setSentiment]       = useState("");
  const [topic,           setTopic]           = useState("");
  const [source,          setSource]          = useState("");
  const [minQuality,      setMinQuality]      = useState<number | undefined>(undefined);

  const load = useCallback(async (reset: boolean, cur: number | null) => {
    setLoading(true);
    try {
      const page = await fetchNews({
        limit: 20,
        cursor: reset ? null : cur,
        sentiment: sentiment || undefined,
        topic:     topic     || undefined,
        source:    source    || undefined,
        min_quality: minQuality,
      }, token);
      setArticles((prev) => reset ? page.items : [...prev, ...page.items]);
      setCursor(page.next_cursor);
      setHasMore(page.next_cursor !== null);
    } catch (e) {
      console.error("fetchNews:", e);
    } finally {
      setLoading(false);
    }
  }, [token, sentiment, topic, source, minQuality]);

  // Reset on filter change
  useEffect(() => {
    setCursor(null);
    load(true, null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sentiment, topic, source, minQuality, token]);

  // Trending + sources once on mount
  useEffect(() => {
    fetchTrending(6, 12, token)
      .then((r) => { setTrending(r.entities ?? []); })
      .catch(() => {})
      .finally(() => setTrendingLoaded(true));
    fetchSources().then(setSources).catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

      {/* Trending */}
      {trendingLoaded && (
        <div>
          <p className="section-label" style={{ marginBottom: 10 }}>{t.trending}</p>
          {trending.length > 0
            ? <TrendingPills
                entities={trending}
                onSelect={(name) => router.push(`/dashboard/search?q=${encodeURIComponent(name)}`)}
              />
            : <span style={{ fontSize: "0.8rem", color: "var(--text3)" }}>{t.noTrending}</span>
          }
        </div>
      )}
      {!trendingLoaded && (
        <div style={{ height: 36, background: "var(--border)", borderRadius: 9999, width: 200,
                      opacity: 0.3, animation: "glow-pulse 2s ease-in-out infinite" }} />
      )}

      {/* Filters */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {[
          {
            value: sentiment, onChange: setSentiment,
            options: SENTIMENT_VALUES.map((v) => ({ value: v, label: SENTIMENT_LABELS[lang][v] ?? v })),
          },
          {
            value: topic, onChange: setTopic,
            options: TOPIC_VALUES.map((v) => ({ value: v, label: TOPIC_LABELS[lang][v] ?? v })),
          },
        ].map(({ value, onChange, options }, i) => (
          <select key={i} value={value} onChange={(e) => onChange(e.target.value)}
                  className="input" style={{ width: "auto", fontSize: "0.84rem" }}>
            {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        ))}
        <select value={source} onChange={(e) => setSource(e.target.value)}
                className="input" style={{ width: "auto", fontSize: "0.84rem" }}>
          <option value="">{t.allSources}</option>
          {sources.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={minQuality?.toString() ?? ""}
                onChange={(e) => setMinQuality(e.target.value ? Number(e.target.value) : undefined)}
                className="input" style={{ width: "auto", fontSize: "0.84rem" }}>
          <option value="">{t.allQualities}</option>
          <option value="0.4">{t.qualityMed}</option>
          <option value="0.6">{t.qualityHigh}</option>
        </select>
      </div>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center" }}>
        <h1 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text)", flex: 1 }}>
          {t.latestNews}
          {articles.length > 0 && (
            <span style={{ color: "var(--text3)", fontWeight: 400, fontSize: "0.82rem", marginLeft: 8 }}>
              ({articles.length})
            </span>
          )}
        </h1>
        <a href="http://localhost:8000/feed.xml" target="_blank"
           style={{ fontSize: "0.75rem", color: "var(--text3)", textDecoration: "none", transition: "color 0.15s" }}
           onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
           onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text3)")}>
          RSS →
        </a>
      </div>

      {/* Skeleton loader */}
      {loading && articles.length === 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card" style={{ opacity: 0.35 }}>
              <div style={{ height: 10, background: "var(--border2)", borderRadius: 4, width: "25%", marginBottom: 14 }} />
              <div style={{ height: 14, background: "var(--border2)", borderRadius: 4, width: "75%", marginBottom: 8 }} />
              <div style={{ height: 12, background: "var(--border2)", borderRadius: 4, width: "55%" }} />
            </div>
          ))}
        </div>
      )}

      {/* Articles */}
      {articles.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {articles.map((a) => <NewsCard key={a.id} article={a} />)}
        </div>
      )}

      {/* Pagination */}
      {hasMore && !loading && (
        <div style={{ textAlign: "center", paddingTop: 8 }}>
          <button onClick={() => load(false, cursor)} className="btn-secondary">{t.loadMore}</button>
        </div>
      )}
      {loading && articles.length > 0 && (
        <div style={{ textAlign: "center", color: "var(--text3)", fontSize: "0.84rem", padding: "8px 0" }}>
          {t.loading}
        </div>
      )}
    </div>
  );
}
