"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Article, RelatedArticle, StorySource } from "@/lib/types";
import { SentimentBadge } from "./SentimentBadge";
import { fetchRelated, fetchStoryCluster } from "@/lib/api";
import { useSettings } from "@/lib/settings-context";
import { useAuth } from "@/lib/auth-context";
import { useSavedArticles } from "@/lib/saved-context";
import { TOPIC_LABELS, UI } from "@/lib/i18n";

function relTime(iso: string, lang: "TR" | "EN") {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  const u = (n: number, tr: string, en: string) => `${Math.round(n)}${lang === "TR" ? tr : en}`;
  if (diff < 60)    return u(diff,       "sn", "s");
  if (diff < 3600)  return u(diff/60,    "dk", "m");
  if (diff < 86400) return u(diff/3600,  "sa", "h");
  return u(diff/86400, "g", "d");
}

// Okuma süresi tahmini (quick win #2, FreshRSS/Miniflux deseni) — içerik
// zaten tam olarak frontend'e geliyor (bkz. NewsResponse.content), backend
// değişikliği gerekmiyor. Ortalama okuma hızı ~200 kelime/dk.
const _WORDS_PER_MINUTE = 200;

function readingTime(content: string | undefined, lang: "TR" | "EN"): string {
  const words = (content ?? "").trim().split(/\s+/).filter(Boolean).length;
  const minutes = Math.max(1, Math.round(words / _WORDS_PER_MINUTE));
  return lang === "TR" ? `${minutes} dk okuma` : `${minutes} min read`;
}

// Kaç kaynağın bu haberi doğruladığı (quick win #1) — veri zaten backend'de
// hesaplanıyor (corroboration_count), sadece burada gösteriliyordu.
function corroborationText(count: number, lang: "TR" | "EN"): string {
  if (lang === "TR") return `${count} kaynak doğruluyor`;
  return `${count} source${count === 1 ? "" : "s"} confirm`;
}

export function NewsCard({ article }: { article: Article }) {
  const { lang } = useSettings();
  const { user } = useAuth();
  const { isSaved, toggleSaved } = useSavedArticles();
  const t = UI[lang];
  const et = user?.effective_tier ?? user?.tier;
  const isPro = et === "pro" || et === "enterprise";
  const [expanded, setExpanded] = useState(false);
  const [related, setRelated] = useState<RelatedArticle[] | null>(null);
  const [loadingRelated, setLoadingRelated] = useState(false);
  const [relatedError, setRelatedError] = useState(false);

  // Story cluster — "bu haberi kim nasıl anlatıyor" (v2.2, herkese açık,
  // related'ın aksine Pro gerektirmez).
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [sources, setSources] = useState<StorySource[] | null>(null);
  const [loadingSources, setLoadingSources] = useState(false);
  const [sourcesError, setSourcesError] = useState(false);

  async function toggleSources() {
    if (sourcesOpen) { setSourcesOpen(false); return; }
    if (sources !== null) { setSourcesOpen(true); return; }
    setLoadingSources(true);
    setSourcesError(false);
    try {
      const r = await fetchStoryCluster(article.id);
      setSources(r.sources ?? []);
    } catch {
      setSourcesError(true);
      setSources([]);
    } finally {
      setLoadingSources(false);
    }
    setSourcesOpen(true);
  }
  const [speaking, setSpeaking] = useState(false);
  // Unmount effect'i (aşağıda) her render'da yeniden kurulmasın diye `speaking`
  // state'inin GÜNCEL değerini bir ref'te aynalıyoruz — effect'in dependency
  // array'i [] olduğu için closure içindeki `speaking` her zaman ilk (false)
  // değerde donardı, ref bunu atlar.
  const speakingRef = useRef(speaking);
  speakingRef.current = speaking;
  // Sunucu hiç `window` görmez, ilk client render'ı da server ile eşleşsin
  // diye `false` başlar — effect'te client'ta gerçek değere geçer. Doğrudan
  // `typeof window` kontrolüyle render etmek server/client hydration
  // uyuşmazlığına yol açardı (bkz. auth-context.tsx'teki aynı desen).
  const [canSpeak, setCanSpeak] = useState(false);
  useEffect(() => {
    setCanSpeak(typeof window !== "undefined" && "speechSynthesis" in window);
    // Kart listeden kaldırılırsa (scroll/yeniden filtreleme) konuşma arkada
    // devam etmesin — sadece BU kart konuşuyorsa durdurur.
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window && speakingRef.current) {
        window.speechSynthesis.cancel();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Tarayıcı-yerel sesli okuma (quick win #4) — ücretsiz Web Speech API,
  // sunucuya hiç istek gitmez. `window.speechSynthesis` yoksa (eski
  // tarayıcı) buton hiç render edilmez, bkz. aşağıdaki JSX.
  function toggleListen() {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const text = [article.title, article.summary].filter(Boolean).join(". ");
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === "TR" ? "tr-TR" : "en-US";
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.cancel();   // aynı anda tek haber okunur
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  }

  async function toggleRelated() {
    if (expanded) { setExpanded(false); return; }
    // Free tier: /api/v1/news/{id}/related sunucuda 403 döner (Pro+ özelliği) —
    // boşuna istek atmak yerine doğrudan yükseltme çağrısı gösteririz.
    if (!isPro) { setExpanded(true); return; }
    if (related !== null) { setExpanded(true); return; }
    setLoadingRelated(true);
    setRelatedError(false);
    try {
      const r = await fetchRelated(article.id);
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
        <span style={{ color: "var(--border2)", fontSize: "0.65rem" }}>•</span>
        <span style={{ fontSize: "0.72rem", color: "var(--text3)" }}>{readingTime(article.content, lang)}</span>
        {topicLabel && (
          <span className="badge" style={{ background: "rgba(0,0,0,.25)", color: "var(--text3)",
                                           borderColor: "var(--border)" }}>
            {topicLabel}
          </span>
        )}
        <SentimentBadge label={article.sentiment_label} />
        <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
          {!!article.corroboration_count && article.corroboration_count > 0 && (
            <span className="badge" title={corroborationText(article.corroboration_count, lang)}
                  style={{ background: "rgba(0,0,0,.25)", color: "var(--text3)", borderColor: "var(--border)" }}>
              🔗 {article.corroboration_count}
            </span>
          )}
          {article.quality_score != null && (
            <span className="badge" style={{ background: "rgba(0,0,0,.25)", color: "var(--text3)",
                                             borderColor: "var(--border)" }}>
              ✦ {(article.quality_score * 100).toFixed(0)}
            </span>
          )}
        </div>
      </div>

      {/* Title */}
      <a href={article.url} target="_blank" rel="noopener noreferrer" style={{
        color: "var(--text)", fontWeight: 700, fontSize: "0.95rem",
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
              background: "var(--accent-soft)",
              color: "var(--accent)",
              borderColor: "var(--accent-line)",
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
            <>
              <span style={{ color: "var(--accent)" }}>↗</span> {t.related}
              {!isPro && (
                <span className="badge" style={{ background: "var(--accent-soft)", color: "var(--accent)",
                                                  borderColor: "var(--accent-line)", fontSize: "0.6rem" }}>
                  PRO
                </span>
              )}
            </>
          )}
        </button>

        {!!article.corroboration_count && article.corroboration_count > 0 && (
          <button onClick={toggleSources} disabled={loadingSources}
                  style={{
                    background: "none", border: "none", cursor: "pointer", padding: 0,
                    fontSize: "0.75rem", color: "var(--text3)", transition: "color 0.15s",
                    display: "flex", alignItems: "center", gap: 4,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text3)")}>
            {loadingSources ? (
              <span style={{ color: "var(--text3)" }}>⟳ {t.loadingRelated}</span>
            ) : sourcesOpen ? (
              <><span style={{ color: "var(--accent)" }}>▲</span> {t.hideSources}</>
            ) : (
              <><span style={{ color: "var(--accent)" }}>🔗</span> {t.storySources}</>
            )}
          </button>
        )}

        {canSpeak && (
          <button onClick={toggleListen} title={speaking ? t.stopListening : t.listenArticle}
                  aria-label={speaking ? t.stopListening : t.listenArticle}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 0,
                           fontSize: "0.85rem", color: speaking ? "var(--accent)" : "var(--text3)",
                           transition: "color 0.15s" }}>
            {speaking ? "⏹" : "🔊"}
          </button>
        )}

        {user && (
          <button onClick={() => toggleSaved(article.id)}
                  title={isSaved(article.id) ? t.unsaveArticle : t.saveArticle}
                  aria-label={isSaved(article.id) ? t.unsaveArticle : t.saveArticle}
                  aria-pressed={isSaved(article.id)}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 0,
                           fontSize: "0.85rem", color: isSaved(article.id) ? "var(--accent)" : "var(--text3)",
                           transition: "color 0.15s" }}>
            {isSaved(article.id) ? "🔖" : "🏷"}
          </button>
        )}

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
          {!isPro && (
            <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px",
                          background: "var(--accent-soft)", border: "1px solid var(--accent-line)",
                          borderRadius: 10 }}>
              <span style={{ fontSize: "0.8rem", color: "var(--text2)", flex: 1 }}>{t.relatedLocked}</span>
              <Link href="/account" className="btn-secondary" style={{ fontSize: "0.72rem", padding: "4px 12px" }}>
                {t.liveUpgrade}
              </Link>
            </div>
          )}
          {isPro && relatedError && (
            <p style={{ fontSize: "0.8rem", color: "var(--neg)", padding: "8px 0" }}>
              ⚠ {t.relatedError}
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

      {/* Story cluster — "bu haberi kim nasıl anlatıyor" (v2.2) */}
      {sourcesOpen && (
        <div style={{ marginTop: 12, paddingTop: 4 }}>
          {sourcesError && (
            <p style={{ fontSize: "0.8rem", color: "var(--neg)", padding: "8px 0" }}>⚠ {t.sourcesError}</p>
          )}
          {!sourcesError && sources?.length === 0 && (
            <p style={{ fontSize: "0.8rem", color: "var(--text3)", padding: "8px 0" }}>{t.noSources}</p>
          )}
          {!sourcesError && sources && sources.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {sources.map((s) => (
                <div key={s.id} className="card-sm" style={{ borderRadius: 10 }}>
                  <a href={s.url} target="_blank" rel="noopener noreferrer" style={{
                    display: "block", fontSize: "0.84rem", color: "var(--text)",
                    fontWeight: 600, textDecoration: "none", transition: "color 0.15s", lineHeight: 1.4,
                  }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text)")}>
                    {s.title}
                  </a>
                  <span style={{ fontSize: "0.72rem", color: "var(--text3)" }}>{s.source}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}
