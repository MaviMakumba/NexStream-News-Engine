"use client";

import { useState } from "react";
import { Navbar } from "@/components/Navbar";
import { submitContact } from "@/lib/api";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

export default function ContactPage() {
  const { lang } = useSettings();
  const t = UI[lang];
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [category, setCategory] = useState<"general" | "takedown">("general");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await submitContact({ name: name || undefined, email, category, message, language: lang });
      setSent(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.contactErrorGeneric);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh" }}>
      <Navbar />
      <div style={{ maxWidth: 560, margin: "0 auto", padding: "40px 20px 80px", display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text)", marginBottom: 6 }}>
            {t.contactPageTitle}
          </h1>
          <p style={{ fontSize: "0.875rem", color: "var(--text3)" }}>{t.contactPageIntro}</p>
        </div>

        <div className="card" style={{ padding: 28 }}>
          {sent ? (
            <p style={{ fontSize: "0.9rem", color: "var(--text2)", lineHeight: 1.6 }}>{t.contactSuccess}</p>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div>
                <label className="label">{t.contactNameLabel}</label>
                <input value={name} onChange={(e) => setName(e.target.value)} className="input" />
              </div>
              <div>
                <label className="label">{t.contactEmailLabel}</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                       className="input" placeholder="siz@ornek.com" required autoComplete="email" />
              </div>
              <div>
                <label className="label">{t.contactCategoryLabel}</label>
                <select value={category} onChange={(e) => setCategory(e.target.value as "general" | "takedown")}
                        className="input">
                  <option value="general">{t.contactCategoryGeneral}</option>
                  <option value="takedown">{t.contactCategoryTakedown}</option>
                </select>
              </div>
              <div>
                <label className="label">{t.contactMessageLabel}</label>
                <textarea value={message} onChange={(e) => setMessage(e.target.value)}
                          className="input" style={{ resize: "none", fontFamily: "inherit" }}
                          rows={6} maxLength={5000} required />
              </div>
              {error && (
                <div style={{ background: "var(--neg-bg)", border: "1px solid var(--neg)", borderRadius: 10,
                              padding: "10px 14px", fontSize: "0.84rem", color: "var(--neg)" }}>
                  ⚠ {error}
                </div>
              )}
              <button type="submit" disabled={loading} className="btn-primary" style={{ justifyContent: "center", padding: "11px" }}>
                {loading ? t.contactSending : t.contactSubmit}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
