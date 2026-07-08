"use client";

// Landing sayfası — kayıt olmadan denenebilen canlı semantik arama demosu.
// `/news/search` (public, auth gerektirmez, 30/dk rate limit) kullanır —
// `dashboard/search/page.tsx`'in kullandığı kota'lı `/api/v1/news/search`'e
// dokunmaz, o sayfanın tier semantiği korunur.

import { useState } from "react";
import Link from "next/link";
import { searchNewsPublic, ApiError } from "@/lib/api";
import type { SearchResult } from "@/lib/types";
import { SentimentBadge } from "./SentimentBadge";
import { useSettings } from "@/lib/settings-context";
import { TOPIC_LABELS, LANDING_SEARCH_EXAMPLES, UI } from "@/lib/i18n";

function relTime(iso: string, lang: "TR" | "EN") {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  const u = (n: number, tr: string, en: string) => `${Math.round(n)}${lang === "TR" ? tr : en}`;
  if (diff < 3600)  return u(diff / 60,    "dk", "m");
  if (diff < 86400) return u(diff / 3600,  "sa", "h");
  return u(diff / 86400, "g", "d");
}

export function LandingSearchDemo() {
  const { lang } = useSettings();
  const t = UI[lang];
  const examples = LANDING_SEARCH_EXAMPLES[lang];

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(q = query) {
    const trimmed = q.trim();
    if (!trimmed) return;
    setQuery(trimmed);
    setLoading(true); setError(""); setResults(null);
    try {
      const r = await searchNewsPublic(trimmed, 5);
      setResults(r ?? []);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 429) {
        setError(t.landingSearchErrorRateLimit);
      } else {
        setError(t.landingSearchErrorGeneric);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", width: "100%" }}>
      <p className="section-label" style={{ textAlign: "center", marginBottom: 8 }}>
        {t.landingSearchLabel}
      </p>
      <h2 style={{ fontSize: "clamp(1.2rem, 3vw, 1.6rem)", fontWeight: 800, color: "var(--text)",
                   textAlign: "center", marginBottom: 18, letterSpacing: "-0.01em" }}>
        {t.landingSearchTitle}
      </h2>

      <form onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
            style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input value={query} onChange={(e) => setQuery(e.target.value)}
               className="input" style={{ flex: 1, fontSize: "0.95rem", padding: "13px 16px" }}
               placeholder={t.landingSearchPlaceholder} />
        <button type="submit" disabled={loading || !query.trim()} className="btn-primary"
                style={{ whiteSpace: "nowrap", padding: "0 22px" }}>
          {loading ? "…" : t.landingSearchBtn}
        </button>
      </form>

      {results === null && !loading && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center", alignItems: "center" }}>
          <span style={{ fontSize: "0.78rem", color: "var(--text3)" }}>{t.landingSearchTryLabel}</span>
          {examples.map((ex) => (
            <button key={ex} onClick={() => handleSearch(ex)} className="pill" style={{ fontSize: "0.78rem" }}>
              {ex}
            </button>
          ))}
        </div>
      )}

      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card-sm" style={{ opacity: 0.35 }}>
              <div style={{ height: 10, background: "var(--border2)", borderRadius: 4, width: "30%", marginBottom: 10 }} />
              <div style={{ height: 13, background: "var(--border2)", borderRadius: 4, width: "80%" }} />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div style={{ background: "var(--neg-bg)", border: "1px solid var(--neg)", borderRadius: 10,
                      padding: "10px 14px", fontSize: "0.84rem", color: "var(--neg)", textAlign: "center" }}>
          ⚠ {error}
        </div>
      )}

      {!loading && !error && results !== null && results.length === 0 && (
        <p style={{ textAlign: "center", fontSize: "0.86rem", color: "var(--text3)", padding: "16px 0" }}>
          {t.landingSearchEmpty}
        </p>
      )}

      {!loading && results !== null && results.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {results.map((r) => {
            const topicLabel = r.topic ? (TOPIC_LABELS[lang]?.[r.topic] ?? r.topic) : null;
            return (
              <a key={r.id} href={r.url} target="_blank" rel="noopener noreferrer"
                 className="card-sm animate-fade-in" style={{ display: "block", textDecoration: "none" }}>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", marginBottom: 4 }}>
                  <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--accent)",
                                 textTransform: "uppercase", letterSpacing: "0.06em" }}>{r.source}</span>
                  <span style={{ color: "var(--border2)", fontSize: "0.65rem" }}>•</span>
                  <span style={{ fontSize: "0.7rem", color: "var(--text3)" }}>{relTime(r.created_at, lang)}</span>
                  {topicLabel && (
                    <span className="badge" style={{ background: "rgba(0,0,0,.25)", color: "var(--text3)",
                                                     borderColor: "var(--border)" }}>{topicLabel}</span>
                  )}
                  <SentimentBadge label={r.sentiment_label} />
                  <span className="badge" style={{
                    background: "var(--accent-soft)", color: "var(--accent)",
                    borderColor: "var(--accent-line)", marginLeft: "auto",
                  }}>
                    {(r.score * 100).toFixed(0)}% {t.landingSearchMatchRate}
                  </span>
                </div>
                <div style={{ color: "var(--text)", fontWeight: 700, fontSize: "0.88rem", lineHeight: 1.4 }}>
                  {r.title}
                </div>
              </a>
            );
          })}

          <Link href="/auth/register" className="btn-secondary"
                style={{ justifyContent: "center", marginTop: 6, fontSize: "0.85rem" }}>
            {t.landingSearchSignupCta}
          </Link>
        </div>
      )}
    </div>
  );
}
