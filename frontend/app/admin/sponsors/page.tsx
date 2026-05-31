"use client";

import { useState } from "react";
import { fetchSponsors, createSponsor, deactivateSponsor } from "@/lib/api";
import type { Sponsor } from "@/lib/types";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

function today(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().split("T")[0];
}

export default function AdminSponsorsPage() {
  const { lang } = useSettings();
  const t = UI[lang];
  const [apiKey,  setApiKey]  = useState("");
  const [sponsors,setSponsors]= useState<Sponsor[]>([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");
  const [loaded,  setLoaded]  = useState(false);

  const [name,        setName]        = useState("");
  const [url,         setUrl]         = useState("");
  const [message,     setMessage]     = useState("");
  const [activeFrom,  setActiveFrom]  = useState(today());
  const [activeUntil, setActiveUntil] = useState(today(30));
  const [saving,      setSaving]      = useState(false);

  async function load(key = apiKey) {
    if (!key.trim()) return;
    setLoading(true); setError("");
    try {
      const data = await fetchSponsors(key);
      setSponsors(data); setLoaded(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.accessDenied);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !url.trim() || !message.trim()) return;
    setSaving(true);
    try {
      await createSponsor(apiKey, {
        name, url, message,
        active_from:  `${activeFrom}T00:00:00Z`,
        active_until: `${activeUntil}T23:59:59Z`,
      });
      setName(""); setUrl(""); setMessage("");
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.genericError);
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(id: number) {
    try { await deactivateSponsor(apiKey, id); await load(); }
    catch (err: unknown) { setError(err instanceof Error ? err.message : t.genericError); }
  }

  const activeSponsor   = sponsors.find((s) => s.is_active);
  const inactiveSponsors = sponsors.filter((s) => !s.is_active);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* API key */}
      <div className="card" style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end" }}>
        <div style={{ flex: "1 1 240px" }}>
          <label className="label">{t.adminKey}</label>
          <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && load()}
                 className="input" placeholder="dev-key-change-me" />
        </div>
        <button onClick={() => load()} disabled={loading || !apiKey.trim()} className="btn-primary">
          {loading ? t.loadingShort : t.show}
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--neg-bg)", border: "1px solid var(--neg)", borderRadius: 12,
                      padding: "12px 16px", fontSize: "0.84rem", color: "var(--neg)" }}>⚠ {error}</div>
      )}

      {loaded && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

          {/* Sponsor list */}
          <div>
            <p className="section-label" style={{ marginBottom: 12 }}>{t.currentSponsors}</p>

            {activeSponsor && (
              <div className="gradient-border" style={{ borderRadius: 14, padding: 20, marginBottom: 12,
                                                        backdropFilter: "blur(14px)", background: "var(--surface)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <span style={{ fontWeight: 700, color: "var(--text)", fontSize: "0.95rem" }}>
                        {activeSponsor.name}
                      </span>
                      <span className="badge" style={{ background: "var(--pos-bg)", color: "var(--pos)",
                                                        borderColor: "var(--pos)" }}>
                        ● {t.activeStatus}
                      </span>
                    </div>
                    <p style={{ fontSize: "0.84rem", color: "var(--text2)", marginBottom: 8, lineHeight: 1.5 }}>
                      {activeSponsor.message}
                    </p>
                    <a href={activeSponsor.url} target="_blank" rel="noopener noreferrer"
                       style={{ fontSize: "0.78rem", color: "var(--accent)", textDecoration: "none" }}>
                      {activeSponsor.url}
                    </a>
                    <div style={{ fontSize: "0.75rem", color: "var(--text3)", marginTop: 6 }}>
                      {activeSponsor.active_from.split("T")[0]} → {activeSponsor.active_until.split("T")[0]}
                    </div>
                  </div>
                  <button onClick={() => handleDeactivate(activeSponsor.id)} className="btn-danger"
                          style={{ padding: "6px 12px", fontSize: "0.78rem", flexShrink: 0 }}>
                    {t.deactivate}
                  </button>
                </div>
              </div>
            )}

            {inactiveSponsors.map((s) => (
              <div key={s.id} className="card" style={{ marginBottom: 8, opacity: 0.55 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <span style={{ fontWeight: 600, color: "var(--text)", fontSize: "0.88rem" }}>{s.name}</span>
                    <div style={{ fontSize: "0.75rem", color: "var(--text3)", marginTop: 4 }}>
                      {s.active_from.split("T")[0]} → {s.active_until.split("T")[0]}
                    </div>
                  </div>
                  <span className="badge" style={{ background: "var(--neu-bg)", color: "var(--neu)",
                                                    borderColor: "var(--neu)" }}>{t.passiveStatus}</span>
                </div>
              </div>
            ))}

            {sponsors.length === 0 && (
              <div className="card" style={{ textAlign: "center", padding: "40px 20px", color: "var(--text3)" }}>
                <div style={{ fontSize: "2rem", marginBottom: 10 }}>⬡</div>
                <p style={{ fontSize: "0.84rem" }}>{t.noSponsors}</p>
              </div>
            )}
          </div>

          {/* Create form */}
          <div>
            <p className="section-label" style={{ marginBottom: 12 }}>{t.newSponsor}</p>
            <div className="card">
              <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <label className="label">{t.sponsorName}</label>
                  <input value={name} onChange={(e) => setName(e.target.value)}
                         className="input" placeholder="Acme Corp" required />
                </div>
                <div>
                  <label className="label">URL</label>
                  <input value={url} onChange={(e) => setUrl(e.target.value)}
                         className="input" placeholder="https://acme.com" required />
                </div>
                <div>
                  <label className="label">{t.messageLabel}</label>
                  <textarea value={message} onChange={(e) => setMessage(e.target.value)}
                            className="input" style={{ resize: "none", fontFamily: "inherit" }}
                            rows={3} placeholder={t.sponsorMsgPlaceholder} required />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label className="label">{t.startLabel}</label>
                    <input type="date" value={activeFrom} onChange={(e) => setActiveFrom(e.target.value)}
                           className="input" />
                  </div>
                  <div>
                    <label className="label">{t.endLabel}</label>
                    <input type="date" value={activeUntil} onChange={(e) => setActiveUntil(e.target.value)}
                           className="input" />
                  </div>
                </div>
                <button type="submit" disabled={saving} className="btn-primary" style={{ justifyContent: "center" }}>
                  {saving ? t.saving : t.addSponsor}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
