"use client";

// Admin iletişim mesajları sayfası (roadmap madde 26, 11 Eylül 2026).
// /contact formundan gelen mesajlar artık DB'ye de yazılıyor — e-posta
// spam'e düşse/gecikse/başarısız olsa bile mesaj burada kaybolmadan görülür.
// Erişim: sponsors sayfasıyla aynı desen — moderator+admin session'ı ile
// otomatik yüklenir, session'sız kullanıcı için paylaşımlı API anahtarı.
// Okundu işaretleme hassas bir mutasyon değil, moderator da yapabilir
// (backend'de sponsor CRUD'un aksine require_admin yok).

import { useCallback, useEffect, useState } from "react";
import { fetchContactMessages, markContactMessageRead, type AdminCreds } from "@/lib/api";
import type { ContactMessage } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

export default function AdminContactMessagesPage() {
  const { user } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];
  const isModerator = Boolean(user?.is_moderator);

  const [apiKey, setApiKey] = useState("");
  const [messages, setMessages] = useState<ContactMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  const creds: AdminCreds = isModerator ? {} : { apiKey };

  const load = useCallback(async (c: AdminCreds = creds) => {
    if (!isModerator && !(c.apiKey ?? "").trim()) return;
    setLoading(true); setError("");
    try {
      const data = await fetchContactMessages(c);
      setMessages(data); setLoaded(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.accessDenied);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isModerator, apiKey, t.accessDenied]);

  useEffect(() => {
    if (isModerator) load({});
  }, [isModerator, load]);

  async function handleMarkRead(id: number) {
    try { await markContactMessageRead(creds, id); await load(); }
    catch (err: unknown) { setError(err instanceof Error ? err.message : t.genericError); }
  }

  const categoryLabel = (c: ContactMessage["category"]) =>
    c === "takedown" ? t.contactCategoryTakedown : t.contactCategoryGeneral;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Auth bar */}
      <div className="card" style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end" }}>
        {isModerator ? (
          <div style={{ flex: "1 1 240px", fontSize: "0.84rem", color: "var(--pos)", paddingBottom: 6 }}>
            ✓ {t.adminAsUser}
          </div>
        ) : (
          <div style={{ flex: "1 1 240px" }}>
            <label className="label">{t.adminKey}</label>
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                   onKeyDown={(e) => e.key === "Enter" && load()}
                   className="input" placeholder="dev-key-change-me" />
          </div>
        )}
        <button onClick={() => load()} disabled={loading || (!isModerator && !apiKey.trim())} className="btn-primary">
          {loading ? t.loadingShort : t.show}
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--neg-bg)", border: "1px solid var(--neg)", borderRadius: 12,
                      padding: "12px 16px", fontSize: "0.84rem", color: "var(--neg)" }}>⚠ {error}</div>
      )}

      {loaded && (
        <div>
          <p className="section-label" style={{ marginBottom: 12 }}>{t.contactMessagesTitle}</p>

          {messages.map((m) => (
            <div key={m.id} className="card" style={{ marginBottom: 10, opacity: m.is_read ? 0.7 : 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
                    <span style={{ fontWeight: 700, color: "var(--text)", fontSize: "0.9rem" }}>
                      {m.name || t.anon}
                    </span>
                    <span style={{ fontSize: "0.78rem", color: "var(--text3)" }}>{m.email}</span>
                    <span className="badge" style={{ background: "var(--neu-bg)", color: "var(--neu)",
                                                      borderColor: "var(--neu)" }}>
                      {categoryLabel(m.category)}
                    </span>
                    <span className="badge" style={{
                      background: m.is_read ? "var(--neu-bg)" : "var(--pos-bg)",
                      color:      m.is_read ? "var(--neu)"    : "var(--pos)",
                      borderColor: m.is_read ? "var(--neu)"   : "var(--pos)",
                    }}>
                      {m.is_read ? t.readStatus : t.unreadStatus}
                    </span>
                  </div>
                  <p style={{ fontSize: "0.86rem", color: "var(--text2)", lineHeight: 1.5, marginBottom: 6,
                              whiteSpace: "pre-wrap" }}>
                    {m.message}
                  </p>
                  <div style={{ fontSize: "0.75rem", color: "var(--text3)" }}>
                    {new Date(m.created_at).toLocaleString(lang === "TR" ? "tr-TR" : "en-US")}
                  </div>
                </div>
                {!m.is_read && (
                  <button onClick={() => handleMarkRead(m.id)} className="btn-secondary"
                          style={{ padding: "6px 12px", fontSize: "0.78rem", flexShrink: 0 }}>
                    {t.markRead}
                  </button>
                )}
              </div>
            </div>
          ))}

          {messages.length === 0 && (
            <div className="card" style={{ textAlign: "center", padding: "40px 20px", color: "var(--text3)" }}>
              <div style={{ fontSize: "2rem", marginBottom: 10 }}>✉</div>
              <p style={{ fontSize: "0.84rem" }}>{t.noContactMessages}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
