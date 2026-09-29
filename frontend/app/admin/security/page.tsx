"use client";

// Admin güvenlik günlüğü (13 Eylül 2026) — backend `GET /admin/security-events`.
// 12 Eylül olayında "bu IP hangi hesapları açtı / bu hesap hangi IP'lerden
// girdi / kim brute force yedi" soruları nginx logu + DB zaman damgası
// eşleştirerek cevaplandı; artık tek ekran. Erişim deseni contact-messages
// sayfasıyla aynı: moderator+ oturumu otomatik, yoksa paylaşımlı API anahtarı.

import { useCallback, useEffect, useState } from "react";
import { fetchSecurityEvents, type AdminCreds, type SecurityEventFilters } from "@/lib/api";
import type { SecurityEvent } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

const EVENT_TYPES = [
  "register", "login_success", "login_failure", "logout",
  "password_reset_requested", "password_reset_done", "email_verified", "account_deleted",
  "admin_access_denied", "api_key_generated", "api_key_revoked",
  "rate_limited", "role_changed", "user_banned", "user_unbanned", "tier_changed",
  "email_verify_failed", "password_reset_failed", "unsubscribe_token_invalid", "webhook_signature_invalid",
  "data_export", "admin_data_changed",
] as const;

// Tek seferde çekilen satır sayısı. Sunucuda sayfalama yok; bu sınıra ulaşılırsa eski olaylar
// SESSİZCE kesilir — kullanıcıya bunu söylemek için limit açıkça gönderilir ve sayılır.
const LIMIT = 200;

const WINDOWS: { hours: number; key: "win1h" | "win24h" | "win7d" | "win30d" | "win90d" }[] = [
  { hours: 1, key: "win1h" }, { hours: 24, key: "win24h" }, { hours: 24 * 7, key: "win7d" },
  { hours: 24 * 30, key: "win30d" }, { hours: 24 * 90, key: "win90d" },
];

// Kategoriye göre rozet rengi — mevcut tema token'ları (pos/neg/neu).
const CATEGORY_STYLE: Record<SecurityEvent["category"], { bg: string; fg: string }> = {
  auth:   { bg: "var(--neu-bg)", fg: "var(--neu)" },
  access: { bg: "var(--neg-bg)", fg: "var(--neg)" },
  abuse:  { bg: "var(--neg-bg)", fg: "var(--neg)" },
  admin:  { bg: "var(--pos-bg)", fg: "var(--pos)" },
};

export default function AdminSecurityPage() {
  const { user } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];
  const isModerator = Boolean(user?.is_moderator);

  const [apiKey, setApiKey] = useState("");
  const [email, setEmail] = useState("");
  const [ip, setIp] = useState("");
  const [eventType, setEventType] = useState("");
  const [hours, setHours] = useState(24);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  const creds: AdminCreds = isModerator ? {} : { apiKey };

  const load = useCallback(async (c: AdminCreds = creds, override?: Partial<SecurityEventFilters>) => {
    if (!isModerator && !(c.apiKey ?? "").trim()) return;
    setLoading(true); setError("");
    const filters: SecurityEventFilters = {
      email: email.trim() || undefined, ip: ip.trim() || undefined,
      event_type: eventType || undefined, hours, limit: LIMIT,
      ...override,
    };
    try {
      setEvents(await fetchSecurityEvents(c, filters)); setLoaded(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.accessDenied);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isModerator, apiKey, email, ip, eventType, hours, t.accessDenied]);

  useEffect(() => {
    if (isModerator) load({});
    // İlk yükleme: sadece oturum varsa, filtre değişimi kullanıcı "Göster"e basınca.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isModerator]);

  // E-posta/IP hücresine tıklama = "bu kimliğin TÜM olayları": diğer filtreler temizlenip HEMEN
  // sorgulanır (eskiden yalnız input dolduruyordu, kullanıcı bir de "Göster"e basmak zorundaydı).
  const pivot = (by: { email?: string; ip?: string }) => {
    setEmail(by.email ?? ""); setIp(by.ip ?? ""); setEventType("");
    load(creds, { email: by.email, ip: by.ip, event_type: undefined });
  };

  const fmt = (iso: string) => new Date(iso).toLocaleString(lang === "TR" ? "tr-TR" : "en-US");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="card" style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end" }}>
        {isModerator ? (
          <div style={{ flex: "1 1 100%", fontSize: "0.84rem", color: "var(--pos)" }}>✓ {t.adminAsUser}</div>
        ) : (
          <div style={{ flex: "1 1 240px" }}>
            <label className="label">{t.adminKey}</label>
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                   className="input" placeholder="dev-key-change-me" />
          </div>
        )}
        <div style={{ flex: "1 1 200px" }}>
          <label className="label">{t.securityFilterEmail}</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} className="input"
                 onKeyDown={(e) => e.key === "Enter" && load()} placeholder="ali@example.com" />
        </div>
        <div style={{ flex: "1 1 160px" }}>
          <label className="label">{t.securityFilterIp}</label>
          <input value={ip} onChange={(e) => setIp(e.target.value)} className="input"
                 onKeyDown={(e) => e.key === "Enter" && load()} placeholder="78.186.147.254" />
        </div>
        <div style={{ flex: "1 1 180px" }}>
          <label className="label">{t.securityFilterEvent}</label>
          <select value={eventType} onChange={(e) => setEventType(e.target.value)} className="input">
            <option value="">{t.securityAllEvents}</option>
            {EVENT_TYPES.map((et) => <option key={et} value={et}>{et}</option>)}
          </select>
        </div>
        <div style={{ flex: "0 1 140px" }}>
          <label className="label">{t.securityFilterWindow}</label>
          <select value={hours} onChange={(e) => setHours(Number(e.target.value))} className="input">
            {WINDOWS.map((w) => <option key={w.hours} value={w.hours}>{t[w.key]}</option>)}
          </select>
        </div>
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
          <p className="section-label" style={{ marginBottom: 12 }}>
            {t.securityEventsTitle} · {events.length}
          </p>
          {events.length >= LIMIT && (
            <p style={{ fontSize: "0.8rem", color: "var(--neg)", marginBottom: 10 }}>
              ⚠ {t.securityTruncated.replace("{n}", String(LIMIT))}
            </p>
          )}
          {events.length === 0 && (
            <p style={{ fontSize: "0.84rem", color: "var(--text3)" }}>{t.noSecurityEvents}</p>
          )}
          {events.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                <thead>
                  <tr style={{ color: "var(--text3)", textAlign: "left" }}>
                    <th style={{ padding: "6px 8px" }}>{t.securityColTime}</th>
                    <th style={{ padding: "6px 8px" }}>{t.securityColEvent}</th>
                    <th style={{ padding: "6px 8px" }}>{t.securityColEmail}</th>
                    <th style={{ padding: "6px 8px" }}>IP</th>
                    <th style={{ padding: "6px 8px" }}>{t.securityColDetail}</th>
                    <th style={{ padding: "6px 8px" }}>request_id</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.id} style={{ borderTop: "1px solid var(--line, rgba(128,128,128,0.2))" }}>
                      <td style={{ padding: "6px 8px", whiteSpace: "nowrap", color: "var(--text2)" }}>{fmt(e.created_at)}</td>
                      <td style={{ padding: "6px 8px", whiteSpace: "nowrap" }}>
                        <span className="badge" style={{
                          background: CATEGORY_STYLE[e.category].bg, color: CATEGORY_STYLE[e.category].fg,
                          borderColor: CATEGORY_STYLE[e.category].fg,
                        }}>{e.event_type}</span>
                      </td>
                      <td style={{ padding: "6px 8px", color: "var(--text)" }}>
                        <button onClick={() => { if (e.email) pivot({ email: e.email }); }} className="tap"
                                style={{ background: "none", border: 0, padding: "0 4px", color: "inherit", cursor: "pointer", font: "inherit" }}
                                title={t.securityFilterByThis}>
                          {e.email ?? "—"}
                        </button>
                        {e.user_id != null && <span style={{ color: "var(--text3)" }}> #{e.user_id}</span>}
                      </td>
                      <td style={{ padding: "6px 8px", whiteSpace: "nowrap" }}>
                        <button onClick={() => { if (e.ip) pivot({ ip: e.ip }); }} className="tap"
                                style={{ background: "none", border: 0, padding: "0 4px", color: "inherit", cursor: "pointer", font: "inherit" }}
                                title={t.securityFilterByThis}>
                          {e.ip ?? "—"}
                        </button>
                      </td>
                      <td style={{ padding: "6px 8px", color: "var(--text2)", maxWidth: 320 }}>
                        {/* Tooltip dokunmatikte çalışmaz: detay kesilmeden (kaydırılabilir tabloda) gösterilir,
                            yol ve user-agent altında küçük yazıyla. */}
                        <div style={{ overflowWrap: "anywhere" }}>{e.detail ?? e.path ?? ""}</div>
                        {e.detail && e.path && (
                          <div style={{ color: "var(--text3)", fontSize: "0.72rem", overflowWrap: "anywhere" }}>{e.path}</div>
                        )}
                        {e.user_agent && (
                          <div style={{ color: "var(--text3)", fontSize: "0.7rem", overflowWrap: "anywhere" }}>{e.user_agent}</div>
                        )}
                      </td>
                      <td style={{ padding: "6px 8px", fontFamily: "monospace", color: "var(--text3)" }}>
                        {e.request_id ? e.request_id.slice(0, 12) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
