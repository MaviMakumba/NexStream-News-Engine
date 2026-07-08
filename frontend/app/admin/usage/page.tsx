"use client";

// Admin kullanım istatistikleri sayfası — salt görüntüleme, moderator+admin erişebilir.
// Erişim (v1.13): moderator/admin rolündeki kullanıcı session'ı ile otomatik
// yüklenir; session'sız kullanıcılar için paylaşımlı API anahtarı girişi gösterilir
// (makine-makine senaryosunun manuel karşılığı).

import { useCallback, useEffect, useState } from "react";
import { fetchUsage } from "@/lib/api";
import type { UsageRow } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

export default function AdminUsagePage() {
  const { user } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];
  const isModerator = Boolean(user?.is_moderator);

  const [apiKey,  setApiKey]  = useState("");
  const [days,    setDays]    = useState(30);
  const [rows,    setRows]    = useState<UsageRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");
  const [loaded,  setLoaded]  = useState(false);

  const load = useCallback(async (key?: string) => {
    // Admin oturumu varsa anahtar gerekmez (cookie otomatik taşınır); yoksa girilen anahtar kullanılır.
    const creds = isModerator ? {} : { apiKey: key ?? apiKey };
    if (!isModerator && !(creds.apiKey ?? "").trim()) return;
    setLoading(true); setError("");
    try {
      const data = await fetchUsage(creds, undefined, days);
      setRows(data.sort((a, b) => b.count - a.count));
      setLoaded(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.accessDenied);
    } finally {
      setLoading(false);
    }
  }, [isModerator, apiKey, days, t.accessDenied]);

  // Admin rolü varsa sayfa açılır açılmaz yükle (gün aralığı değişince de).
  useEffect(() => {
    if (isModerator) load();
  }, [isModerator, days, load]);

  const total = rows.reduce((s, r) => s + r.count, 0);
  const avgMs = rows.length ? Math.round(rows.reduce((s, r) => s + r.avg_ms, 0) / rows.length) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Auth bar: admin'e bilgi notu, diğerlerine API key girişi */}
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
        <div>
          <label className="label">{t.dayRange}</label>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}
                  className="input" style={{ width: 120, fontSize: "0.84rem" }}>
            {[7, 14, 30, 90].map((d) => <option key={d} value={d}>{d} {t.dayUnit}</option>)}
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
        <>
          {/* KPI cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
            {[
              { value: total.toLocaleString(), label: t.totalReq, color: "var(--accent)" },
              { value: rows.length,            label: t.uniqueEndpoint, color: "var(--accent2)" },
              { value: `${avgMs}ms`,           label: t.avgResp, color: "var(--pos)" },
            ].map((kpi) => (
              <div key={kpi.label} className="card" style={{ textAlign: "center" }}>
                <div style={{ fontSize: "1.8rem", fontWeight: 800, color: kpi.color, lineHeight: 1.2, marginBottom: 4 }}>
                  {kpi.value}
                </div>
                <div className="section-label">{kpi.label}</div>
              </div>
            ))}
          </div>

          {/* Table */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.84rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {[t.colUserId, t.colEndpoint, t.colReq, t.colAvgMs].map((h, i) => (
                      <th key={h} style={{
                        padding: "14px 20px", textAlign: i >= 2 ? "right" : "left",
                        color: "var(--text3)", fontWeight: 700, textTransform: "uppercase",
                        letterSpacing: "0.06em", fontSize: "0.7rem",
                      }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid var(--border)", transition: "background 0.1s" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--border)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "")}>
                      <td style={{ padding: "12px 20px", color: r.user_id ? "var(--text)" : "var(--text3)",
                                   fontFamily: "monospace", fontSize: "0.82rem" }}>
                        {r.user_id ?? <span style={{ fontStyle: "italic" }}>{t.anon}</span>}
                      </td>
                      <td style={{ padding: "12px 20px", color: "var(--accent)", fontFamily: "monospace",
                                   fontSize: "0.8rem" }}>
                        {r.endpoint}
                      </td>
                      <td style={{ padding: "12px 20px", textAlign: "right" }}>
                        <span className="badge" style={{ background: "var(--accent-soft)",
                                                          color: "var(--accent)", borderColor: "var(--accent-line)" }}>
                          {r.count}
                        </span>
                      </td>
                      <td style={{ padding: "12px 20px", textAlign: "right", color: "var(--text3)",
                                   fontFamily: "monospace", fontSize: "0.82rem" }}>
                        {r.avg_ms.toFixed(1)}ms
                      </td>
                    </tr>
                  ))}
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={4} style={{ padding: "40px", textAlign: "center", color: "var(--text3)" }}>
                        {t.noRecords}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
