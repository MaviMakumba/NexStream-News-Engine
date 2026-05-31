"use client";

import { useState } from "react";
import { fetchUsage } from "@/lib/api";
import type { UsageRow } from "@/lib/types";

export default function AdminUsagePage() {
  const [apiKey,  setApiKey]  = useState("");
  const [days,    setDays]    = useState(30);
  const [rows,    setRows]    = useState<UsageRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");
  const [loaded,  setLoaded]  = useState(false);

  async function load() {
    if (!apiKey.trim()) return;
    setLoading(true); setError("");
    try {
      const data = await fetchUsage(apiKey, undefined, days);
      setRows(data.sort((a, b) => b.count - a.count));
      setLoaded(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erişim reddedildi.");
    } finally {
      setLoading(false);
    }
  }

  const total = rows.reduce((s, r) => s + r.count, 0);
  const avgMs = rows.length ? Math.round(rows.reduce((s, r) => s + r.avg_ms, 0) / rows.length) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* API key bar */}
      <div className="card" style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end" }}>
        <div style={{ flex: "1 1 240px" }}>
          <label className="label">Admin API Anahtarı</label>
          <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && load()}
                 className="input" placeholder="dev-key-change-me" />
        </div>
        <div>
          <label className="label">Gün Aralığı</label>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}
                  className="input" style={{ width: 120, fontSize: "0.84rem" }}>
            {[7, 14, 30, 90].map((d) => <option key={d} value={d}>{d} gün</option>)}
          </select>
        </div>
        <button onClick={load} disabled={loading || !apiKey.trim()} className="btn-primary">
          {loading ? "Yükleniyor…" : "Göster"}
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
              { value: total.toLocaleString(), label: "Toplam İstek", color: "var(--accent)" },
              { value: rows.length,            label: "Benzersiz Endpoint", color: "var(--accent2)" },
              { value: `${avgMs}ms`,           label: "Ort. Yanıt Süresi", color: "var(--pos)" },
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
                    {["User ID", "Endpoint", "İstek", "Ort. ms"].map((h, i) => (
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
                        {r.user_id ?? <span style={{ fontStyle: "italic" }}>anonim</span>}
                      </td>
                      <td style={{ padding: "12px 20px", color: "var(--accent)", fontFamily: "monospace",
                                   fontSize: "0.8rem" }}>
                        {r.endpoint}
                      </td>
                      <td style={{ padding: "12px 20px", textAlign: "right" }}>
                        <span className="badge" style={{ background: "rgba(34,211,238,.08)",
                                                          color: "var(--accent)", borderColor: "rgba(34,211,238,.2)" }}>
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
                        Kayıt bulunamadı.
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
