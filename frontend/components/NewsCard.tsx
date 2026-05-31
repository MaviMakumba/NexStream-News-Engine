"use client";

import { useState } from "react";
import type { Article, RelatedArticle } from "@/lib/types";
import { SentimentBadge } from "./SentimentBadge";
import { fetchRelated } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { TOPIC_LABELS, UI } from "@/lib/i18n";

function relTime(iso: string, lang: "TR" | "EN") {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  const u = (n: number, tr: string, en: string) => `${Math.round(n)}${lang === "TR" ? tr : en}`;
  if (diff < 60)    return u(diff,       "sn", "s");
  if (diff < 3600)  return u(diff/60,    "dk", "m");
  if (diff < 86400) return u(diff/3600,  "sa", "h");
  return u(diff/86400, "g", "d");
}

export function NewsCard({ article }: { article: Article }) {
  const { token } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];
  const [expanded, setExpanded] = useState(false);
  const [related, setRelated] = useState<RelatedArticle[] | null>(null);
  const [loadingRelated, setLoadingRelated] = useState(false);
  const [relatedError, setRelatedError] = useState(false);

  async function toggleRelated() {
    if (expanded) { setExpanded(false); return; }
    if (related !== null) { setExpanded(true); return; }
    setLoadingRelated(true);
    setRelatedError(false);
    try {
      const r = await fetchRelated(article.id, token);
      setRelated(r.related ?? []);
    } catch {
      setRelatedError(true);
      setRelated([]);
    } finally {
      setLoadingRelated(false);
    }
    setExpanded(true);
  }

  const topicLabel = article.topic ? (TOPIC_LABELS[lang]?.[article.topic] ?? article.topic) : null;
  const entities = [
    ...(article.entities?.persons ?? []),
    ...(article.entities?.organizations ?? []),
    ...(article.entities?.locations ?? []),
  ].slice(0, 5);

  return (
    <article className="card animate-fade-in" style={{ cursor: "default" }}>

      {/* Meta */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", marginBottom: 10 }}>
        <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase",
                       letterSpacing: "0.06em" }}>
          {article.source}
        </span>
        <span style={{ color: "var(--border2)", fontSize: "0.65rem" }}>•</span>
        <span style={{ fontSize: "0.72rem", color: "var(--text3)" }}>{relTime(article.created_at, lang)}</span>
        {topicLabel && (
          <span className="badge" style={{ background: "rgba(0,0,0,.25)", color: "var(--text3)",
                                           borderColor: "var(--border)" }}>
            {topicLabel}
          </span>
        )}
        <SentimentBadge label={article.sentiment_label} />
        {article.quality_score != null && (
          <span className="badge" style={{ background: "rgba(0,0,0,.25)", color: "var(--text3)",
                                           borderColor: "var(--border)", marginLeft: "auto" }}>
            ✦ {(article.quality_score * 100).toFixed(0)}
          </span>
        )}
      </div>

      {/* Title */}
      <a href={article.url} target="_blank" rel="noopener noreferrer" style={{
        display: "block", color: "var(--text)", fontWeight: 700, fontSize: "0.95rem",
        lineHeight: 1.45, textDecoration: "none", transition: "color 0.15s",
        overflow: "hidden", display: "-webkit-box" as any,
        WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any,
      }}
        onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
        onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text)")}>
        {article.title}
      </a>

      {/* Summary */}
      {article.summary && (
        <p style={{
          marginTop: 8, fontSize: "0.84rem", color: "var(--text2)", lineHeight: 1.6,
          overflow: "hidden", display: "-webkit-box" as any,
          WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any,
        }}>
          {article.summary}
        </p>
      )}

      {/* Entity chips */}
      {entities.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 5 }}>
          {entities.map((e) => (
            <span key={e} className="badge" style={{
              background: "rgba(34,211,238,.05)",
              color: "var(--accent)",
              borderColor: "rgba(34,211,238,.2)",
              fontSize: "0.68rem",
            }}>
              {e}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)",
                    display: "flex", alignItems: "center", gap: 12 }}>
        <button onClick={toggleRelated} disabled={loadingRelated}
                style={{
                  background: "none", border: "none", cursor: "pointer", padding: 0,
                  fontSize: "0.75rem", color: "var(--text3)", transition: "color 0.15s",
                  display: "flex", alignItems: "center", gap: 4,
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text3)")}>
          {loadingRelated ? (
            <span style={{ color: "var(--text3)" }}>⟳ {t.loadingRelated}</span>
          ) : expanded ? (
            <><span style={{ color: "var(--accent)" }}>▲</span> {t.hideRelated}</>
          ) : (
            <><span style={{ color: "var(--accent)" }}>↗</span> {t.related}</>
          )}
        </button>

        <a href={article.url} target="_blank" rel="noopener noreferrer"
           style={{ fontSize: "0.75rem", color: "var(--text3)", textDecoration: "none",
                    marginLeft: "auto", transition: "color 0.15s" }}
           onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
           onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text3)")}>
          {t.goToArticle}
        </a>
      </div>

      {/* Related */}
      {expanded && (
        <div style={{ marginTop: 12, paddingTop: 4 }}>
          {relatedError && (
            <p style={{ fontSize: "0.8rem", color: "var(--neg)", padding: "8px 0" }}>
              ⚠ İlgili haberler yüklenemedi.
            </p>
          )}
          {!relatedError && related?.length === 0 && (
            <p style={{ fontSize: "0.8rem", color: "var(--text3)", padding: "8px 0" }}>{t.noRelated}</p>
          )}
          {!relatedError && related && related.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {related.map((r) => (
                <div key={r.id} className="card-sm" style={{ borderRadius: 10 }}>
                  <a href={r.url} target="_blank" rel="noopener noreferrer" style={{
                    display: "block", fontSize: "0.84rem", color: "var(--text)",
                    fontWeight: 600, textDecoration: "none", transition: "color 0.15s", lineHeight: 1.4,
                  }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text)")}>
                    {r.title}
                  </a>
                  <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                    <span style={{ fontSize: "0.72rem", color: "var(--text3)" }}>{r.source}</span>
                    {(r.common_entities ?? []).slice(0, 3).map((e) => (
                      <span key={e} className="badge"
                            style={{ background: "rgba(0,0,0,.2)", color: "var(--text3)", borderColor: "var(--border)" }}>
                        {e}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}
