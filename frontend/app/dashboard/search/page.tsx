"use client";

import { useState, useEffect } from "react";
import { useSettings } from "@/lib/settings-context";
import { searchNews } from "@/lib/api";
import type { SearchResult } from "@/lib/types";
import { SentimentBadge } from "@/components/SentimentBadge";
import { TOPIC_LABELS, UI } from "@/lib/i18n";

const HISTORY_KEY = "nxt_search_history";
const MAX_HISTORY = 8;

function getHistory(): string[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]"); } catch { return []; }
}

function saveHistory(q: string) {
  const prev = getHistory().filter((h) => h !== q);
  localStorage.setItem(HISTORY_KEY, JSON.stringify([q, ...prev].slice(0, MAX_HISTORY)));
}

function relTime(iso: string) {
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  if (d < 3600)  return `${Math.round(d / 60)}dk`;
  if (d < 86400) return `${Math.round(d / 3600)}sa`;
  return `${Math.round(d / 86400)}g`;
}

export default function SearchPage() {
  const { lang } = useSettings();
  const t = UI[lang];
  const [query,    setQuery]    = useState("");
  const [nResults, setNResults] = useState(10);
  const [results,  setResults]  = useState<SearchResult[]>([]);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");
  const [searched, setSearched] = useState(false);
  const [history,  setHistory]  = useState<string[]>([]);

  useEffect(() => {
    setHistory(getHistory());
    // Trending pill / deep link: ?q=... otomatik arama tetikler.
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) { setQuery(q); handleSearch(q); }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSearch(q = query) {
    const trimmed = q.trim();
    if (!trimmed) return;
    setLoading(true); setError(""); setSearched(true);
    try {
      const r = await searchNews(trimmed, nResults);
      setResults(r ?? []);
      saveHistory(trimmed);
      setHistory(getHistory());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.searchFailed);
    } finally {
      setLoading(false);
    }
  }

  function removeHistory(q: string) {
    const next = getHistory().filter((h) => h !== q);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
    setHistory(next);
  }

  return (
    <div style={{ maxWidth: 820, margin: "0 auto" }}>
      <div style={{ marginBottom: 28 }}>
        <p className="section-label" style={{ marginBottom: 8 }}>{t.search}</p>
        <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text)", letterSpacing: "-0.02em", marginBottom: 6 }}>
          {t.semanticSearch}
        </h1>
        <p style={{ color: "var(--text3)", fontSize: "0.84rem" }}>{t.semanticDesc}</p>
      </div>

      {/* Search form */}
      <form onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
            style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        <input value={query} onChange={(e) => setQuery(e.target.value)}
               className="input" style={{ flex: "1 1 180px", fontSize: "0.9rem", minWidth: 0 }}
               placeholder={t.searchPlaceholder} autoFocus />
        <select value={nResults} onChange={(e) => setNResults(Number(e.target.value))}
                className="input" style={{ width: 72, fontSize: "0.84rem" }}>
          {[5, 10, 20, 30].map((n) => <option key={n}>{n}</option>)}
        </select>
        <button type="submit" disabled={loading || !query.trim()} className="btn-primary"
                style={{ whiteSpace: "nowrap", padding: "9px 20px" }}>
          {loading ? "…" : t.searchBtn}
        </button>
      </form>

      {/* History */}
      {history.length > 0 && (
        <div style={{ marginBottom: 20, display: "flex", alignItems: "center", flexWrap: "wrap", gap: 6 }}>
          <span className="section-label" style={{ marginRight: 4, flexShrink: 0 }}>{t.searchHistory}</span>
          {history.map((h) => (
            <span key={h} style={{ display: "inline-flex", alignItems: "center", gap: 0 }}>
              <button onClick={() => { setQuery(h); handleSearch(h); }}
                      className="pill" style={{ borderRadius: "9999px 0 0 9999px", paddingRight: 6 }}>
                {h}
              </button>
              <button onClick={() => removeHistory(h)}
                      aria-label={`${t.removeFromHistory}: ${h}`}
                      style={{
                        background: "var(--surface)", border: "1px solid var(--border)",
                        borderLeft: "none", borderRadius: "0 9999px 9999px 0",
                        padding: "4px 8px", cursor: "pointer", fontSize: "0.7rem",
                        color: "var(--text3)", lineHeight: 1, transition: "all 0.15s",
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = "var(--neg)"; e.currentTarget.style.borderColor = "var(--neg)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text3)"; e.currentTarget.style.borderColor = "var(--border)"; }}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ background: "var(--neg-bg)", border: "1px solid var(--neg)", borderRadius: 10,
                      padding: "10px 14px", fontSize: "0.84rem", color: "var(--neg)", marginBottom: 16 }}>
          ⚠ {error}
        </div>
      )}

      {/* Empty state */}
      {searched && !loading && results.length === 0 && !error && (
        <div style={{ textAlign: "center", padding: "56px 0", color: "var(--text3)" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: 12, opacity: 0.5 }}>⬡</div>
          <p style={{ fontSize: "0.9rem" }}>"{query}" {t.noResults}</p>
        </div>
      )}

      {/* Results */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {results.map((r, i) => {
          const topicLabel = r.topic ? (TOPIC_LABELS[lang]?.[r.topic] ?? r.topic) : null;
          return (
            <article key={r.id} className="card animate-fade-in"
                     style={{ animationDelay: `${i * 50}ms` }}>
              <div style={{ display: "flex", gap: 16 }}>
                <span className="gradient-text" style={{ fontSize: "1.5rem", fontWeight: 900,
                                                          flexShrink: 0, width: 28, lineHeight: 1.2, paddingTop: 2 }}>
                  {i + 1}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--accent)",
                                   textTransform: "uppercase", letterSpacing: "0.06em" }}>{r.source}</span>
                    <span style={{ color: "var(--border2)", fontSize: "0.65rem" }}>•</span>
                    <span style={{ fontSize: "0.72rem", color: "var(--text3)" }}>{relTime(r.created_at)}</span>
                    {topicLabel && (
                      <span className="badge" style={{ background: "rgba(0,0,0,.25)", color: "var(--text3)",
                                                       borderColor: "var(--border)" }}>{topicLabel}</span>
                    )}
                    <SentimentBadge label={r.sentiment_label} />
                    <span className="badge" style={{
                      background: "var(--accent-soft)", color: "var(--accent)",
                      borderColor: "var(--accent-line)", marginLeft: "auto",
                    }}>
                      {(r.score * 100).toFixed(0)}% {t.matchRate}
                    </span>
                  </div>
                  <a href={r.url} target="_blank" rel="noopener noreferrer" style={{
                    display: "block", color: "var(--text)", fontWeight: 700, fontSize: "0.95rem",
                    textDecoration: "none", lineHeight: 1.4, transition: "color 0.15s",
                  }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text)")}>
                    {r.title}
                  </a>
                  {r.summary && (
                    <p style={{ marginTop: 6, fontSize: "0.84rem", color: "var(--text2)", lineHeight: 1.6,
                                overflow: "hidden", display: "-webkit-box" as any,
                                WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any }}>
                      {r.summary}
                    </p>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
