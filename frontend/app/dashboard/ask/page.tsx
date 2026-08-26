"use client";

// RAG soru-cevap sayfası (roadmap #13). Genel sohbet ile habere özel sohbet
// (?articleId=N) TAMAMEN ayrı state'lerde tutulur — sayfa yenilenince/kapanınca
// kaybolur (bilinçli karar, kalıcı sohbet geçmişi YOK, bkz. spec "Kapsam dışı").

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSettings } from "@/lib/settings-context";
import { useAuth } from "@/lib/auth-context";
import { askQuestion, ApiError } from "@/lib/api";
import type { AskMessage, RagAnswerResponse } from "@/lib/types";
import { UI } from "@/lib/i18n";

// Kaynak URL'leri backend'in evidence_bundle'ından (Article.url) geliyor —
// RSS scraping'den, doğrudan kullanıcı girdisi değil. Yine de bu sayfa bir
// LLM sentezinin çıktısına bağlı olduğu için, tıklanabilir bir link olarak
// render etmeden önce http(s) şeması dışındakileri (ör. javascript:) elemek
// ucuz ve zarasız bir savunma katmanı (bkz. otomatik güvenlik incelemesi).
function isSafeHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

type SessionId = "general" | `article:${number}`;

interface ChatMessage extends AskMessage {
  meta?: RagAnswerResponse;
}

export default function AskPage() {
  const { lang } = useSettings();
  const { user } = useAuth();
  const t = UI[lang];
  const et = user?.effective_tier ?? user?.tier;
  const isPro = et === "pro" || et === "enterprise";

  const [articleId, setArticleId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<Record<string, ChatMessage[]>>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const idParam = new URLSearchParams(window.location.search).get("articleId");
    setArticleId(idParam ? Number(idParam) : null);
  }, []);

  const sessionId: SessionId = articleId != null ? (`article:${articleId}` as const) : "general";
  const messages = sessions[sessionId] ?? [];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  async function handleSend() {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setError("");
    const history = messages.map(({ role, content }) => ({ role, content }));
    const userMsg: ChatMessage = { role: "user", content: question };
    setSessions((cur) => ({ ...cur, [sessionId]: [...(cur[sessionId] ?? []), userMsg] }));
    setBusy(true);
    try {
      const res = await askQuestion({ question, article_id: articleId, history });
      const assistantMsg: ChatMessage = { role: "assistant", content: res.answer, meta: res };
      setSessions((cur) => ({ ...cur, [sessionId]: [...(cur[sessionId] ?? []), assistantMsg] }));
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : t.askErrorGeneric);
    } finally {
      setBusy(false);
    }
  }

  if (!isPro) {
    return (
      <div style={{ maxWidth: 640, margin: "60px auto", textAlign: "center" }}>
        <p style={{ color: "var(--text2)", marginBottom: 16 }}>{t.askLocked}</p>
        <Link href="/account" className="btn-primary">{t.liveUpgrade}</Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", flexDirection: "column",
                  height: "calc(100vh - 140px)" }}>
      <div style={{ marginBottom: 16 }}>
        <p className="section-label" style={{ marginBottom: 8 }}>{t.askNavLabel}</p>
        <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text)", letterSpacing: "-0.02em" }}>
          {t.askPageTitle}
        </h1>
        <p style={{ color: "var(--text3)", fontSize: "0.84rem" }}>{t.askPageDesc}</p>
        {articleId != null && (
          <Link href="/dashboard/ask" style={{ fontSize: "0.78rem", color: "var(--accent)", display: "inline-block", marginTop: 6 }}>
            ← {t.askBackToGeneral}
          </Link>
        )}
      </div>

      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12, padding: "8px 0" }}>
        {messages.length === 0 && (
          <p style={{ color: "var(--text3)", textAlign: "center", marginTop: 40, fontSize: "0.88rem" }}>
            {t.askEmptyState}
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "85%" }}>
            <div className="card-sm" style={{
              background: m.role === "user" ? "var(--accent-soft)" : "var(--surface)",
              borderRadius: 12, padding: "10px 14px",
            }}>
              <p style={{ fontSize: "0.88rem", color: "var(--text)", whiteSpace: "pre-wrap", lineHeight: 1.5, margin: 0 }}>
                {m.content}
              </p>
              {m.meta && (
                <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
                  <span className="badge" style={{
                    background: "var(--accent-soft)", color: "var(--accent)", borderColor: "var(--accent-line)",
                  }}>
                    {m.meta.coverage === "full" ? t.askCoverageFull
                      : m.meta.coverage === "partial" ? t.askCoveragePartial : t.askCoverageNone}
                  </span>
                  {m.meta.corroboration_level !== "none" && (
                    <span className="badge" style={{ background: "var(--surface)", color: "var(--text3)", borderColor: "var(--border)" }}>
                      {m.meta.corroboration_level === "multi_source" ? t.askCorroborationMulti : t.askCorroborationSingle}
                    </span>
                  )}
                </div>
              )}
              {m.meta && m.meta.sources.length > 0 && (
                <div style={{ marginTop: 8, fontSize: "0.78rem", color: "var(--text3)" }}>
                  {t.askSourcesLabel}{" "}
                  {m.meta.sources.map((s) => (
                    isSafeHttpUrl(s.url) ? (
                      <a key={s.index} href={s.url} target="_blank" rel="noopener noreferrer"
                         style={{ color: "var(--accent)", marginRight: 8 }}>
                        [{s.index}] {s.source}
                      </a>
                    ) : (
                      <span key={s.index} style={{ color: "var(--text3)", marginRight: 8 }}>
                        [{s.index}] {s.source}
                      </span>
                    )
                  ))}
                </div>
              )}
              {m.meta?.suggest_alert && (
                <Link href={`/account?prefillKeyword=${encodeURIComponent(messages[i - 1]?.content ?? "")}`}
                      className="btn-secondary" style={{ marginTop: 8, fontSize: "0.78rem", display: "inline-block" }}>
                  {t.askSuggestAlertBtn}
                </Link>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && <p style={{ color: "var(--neg)", fontSize: "0.82rem", marginTop: 8 }}>⚠ {error}</p>}

      <form onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            style={{ display: "flex", gap: 8, marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
        <input value={input} onChange={(e) => setInput(e.target.value)}
               className="input" style={{ flex: 1, minWidth: 0 }} placeholder={t.askPlaceholder}
               disabled={busy} autoFocus />
        <button type="submit" disabled={busy || !input.trim()} className="btn-primary"
                style={{ whiteSpace: "nowrap", padding: "9px 20px" }}>
          {busy ? t.askThinking : t.askSendBtn}
        </button>
      </form>
    </div>
  );
}
