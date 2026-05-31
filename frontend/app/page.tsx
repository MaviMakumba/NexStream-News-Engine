"use client";

import Link from "next/link";
import { Navbar } from "@/components/Navbar";

const FEATURES = [
  {
    icon: "◈",
    title: "AI Sentiment Analizi",
    desc: "Groq llama-3.1 ile her haberin duygu durumu, entity tanıma ve konu sınıflandırması saniyeler içinde.",
    accent: "#22d3ee",
  },
  {
    icon: "⬡",
    title: "Semantik Arama",
    desc: "ChromaDB vektör veritabanı ile anlamsal arama — aradığın kelime haberde olmasa bile bulur.",
    accent: "#a78bfa",
  },
  {
    icon: "◎",
    title: "Canlı Haber Akışı",
    desc: "WebSocket ile yeni haberler anında ekrana düşüyor. 17 kaynak, sürekli güncellenen feed.",
    accent: "#4ade80",
  },
];

const PRICING = [
  {
    tier: "Ücretsiz",
    price: "$0",
    period: "",
    features: ["100 API isteği / gün", "Haberler & semantik arama", "Günlük digest e-posta", "10 arama sonucu"],
    cta: "Hemen Başla",
    href: "/auth/register",
    highlight: false,
  },
  {
    tier: "Pro",
    price: "$9.99",
    period: "/ay",
    features: ["2.000 API isteği / gün", "WebSocket canlı akış", "50 arama sonucu", "Anlık keyword alert", "İlişki grafı"],
    cta: "Pro'ya Geç",
    href: "/auth/register",
    highlight: true,
  },
  {
    tier: "Kurumsal",
    price: "$49.99",
    period: "/ay",
    features: ["Sınırsız API isteği", "Ham veri export", "Özel kaynak ekleme", "SLA garantisi", "Öncelikli destek"],
    cta: "İletişime Geç",
    href: "/auth/register",
    highlight: false,
  },
];

export default function LandingPage() {
  return (
    <div style={{ minHeight: "100vh", overflowX: "hidden" }}>
      <Navbar />

      {/* Hero */}
      <section style={{ position: "relative", padding: "100px 20px 80px", textAlign: "center" }}>
        {/* Grid background */}
        <div className="grid-bg" style={{
          position: "absolute", inset: 0, zIndex: 0, pointerEvents: "none",
          maskImage: "radial-gradient(ellipse 80% 60% at 50% 0%, black, transparent)",
        }} />

        {/* Glow orbs */}
        <div style={{
          position: "absolute", top: 0, left: "25%", width: 600, height: 300,
          background: "radial-gradient(ellipse, rgba(34,211,238,.07) 0%, transparent 70%)",
          pointerEvents: "none", zIndex: 0,
        }} />
        <div style={{
          position: "absolute", top: 50, right: "15%", width: 400, height: 250,
          background: "radial-gradient(ellipse, rgba(167,139,250,.06) 0%, transparent 70%)",
          pointerEvents: "none", zIndex: 0,
        }} />

        <div style={{ position: "relative", zIndex: 1, maxWidth: 800, margin: "0 auto" }}>
          {/* Status pill */}
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 8,
            background: "rgba(34,211,238,.06)", border: "1px solid rgba(34,211,238,.18)",
            borderRadius: 9999, padding: "6px 16px", marginBottom: 32, fontSize: "0.8rem",
            color: "rgba(34,211,238,.9)",
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: "50%", background: "#22d3ee",
              boxShadow: "0 0 8px #22d3ee",
              animation: "glow-pulse 2s ease-in-out infinite",
              display: "inline-block",
            }} />
            Canlı — 825+ haber indekslendi, 17 kaynak aktif
          </div>

          {/* Heading */}
          <h1 style={{
            fontSize: "clamp(2.4rem, 6vw, 4rem)", fontWeight: 900, lineHeight: 1.1,
            letterSpacing: "-0.03em", marginBottom: 24, color: "var(--text)",
          }}>
            Türkiye Haberlerini
            <br />
            <span className="gradient-text">Yapay Zeka ile</span> Keşfet
          </h1>

          <p style={{
            fontSize: "1.1rem", color: "var(--text2)", maxWidth: 520, margin: "0 auto 40px",
            lineHeight: 1.7,
          }}>
            17 kaynaktan gerçek zamanlı akış. Duygu analizi, entity tanıma,
            semantik arama ve ilişki grafı — tek platformda.
          </p>

          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/auth/register" className="btn-primary" style={{ fontSize: "0.95rem", padding: "11px 28px" }}>
              Ücretsiz Başla →
            </Link>
            <Link href="/dashboard" className="btn-secondary" style={{ fontSize: "0.95rem", padding: "11px 28px" }}>
              Demo Görüntüle
            </Link>
          </div>
        </div>

        {/* Stats row */}
        <div style={{
          position: "relative", zIndex: 1,
          display: "flex", justifyContent: "center", gap: 48, marginTop: 64,
          flexWrap: "wrap",
        }}>
          {[
            { value: "825+", label: "Haber İndekslendi" },
            { value: "17",   label: "Aktif Kaynak" },
            { value: "<2sn", label: "Analiz Süresi" },
            { value: "100%", label: "Ücretsiz Başlangıç" },
          ].map((s) => (
            <div key={s.label} style={{ textAlign: "center" }}>
              <div className="gradient-text" style={{ fontSize: "1.8rem", fontWeight: 800, lineHeight: 1 }}>
                {s.value}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text3)", marginTop: 4, textTransform: "uppercase",
                            letterSpacing: "0.08em" }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section style={{ maxWidth: 1100, margin: "0 auto", padding: "60px 20px" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <p className="section-label" style={{ marginBottom: 10 }}>Özellikler</p>
          <h2 style={{ fontSize: "1.9rem", fontWeight: 800, color: "var(--text)", letterSpacing: "-0.02em" }}>
            Güçlü Altyapı, Sade Arayüz
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
          {FEATURES.map((f) => (
            <div key={f.title} className="card" style={{ position: "relative", overflow: "hidden" }}>
              <div style={{
                position: "absolute", top: 0, right: 0, width: 150, height: 150,
                background: `radial-gradient(circle, ${f.accent}10, transparent 70%)`,
                pointerEvents: "none",
              }} />
              <div style={{
                width: 44, height: 44, borderRadius: 12, marginBottom: 16,
                background: `${f.accent}15`, border: `1px solid ${f.accent}30`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "1.3rem", color: f.accent,
              }}>
                {f.icon}
              </div>
              <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
                {f.title}
              </h3>
              <p style={{ fontSize: "0.875rem", color: "var(--text2)", lineHeight: 1.65 }}>
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section style={{ maxWidth: 1100, margin: "0 auto", padding: "40px 20px 80px" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <p className="section-label" style={{ marginBottom: 10 }}>Fiyatlandırma</p>
          <h2 style={{ fontSize: "1.9rem", fontWeight: 800, color: "var(--text)", letterSpacing: "-0.02em" }}>
            Ücretsiz başla, büyüdükçe yükselt
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 20 }}>
          {PRICING.map((p) => (
            <div key={p.tier} className={p.highlight ? "gradient-border" : "card"}
                 style={{
                   ...(p.highlight ? {
                     borderRadius: 14, padding: 20,
                     background: "var(--surface)", backdropFilter: "blur(14px)",
                     boxShadow: "0 0 40px var(--glow)",
                   } : {}),
                   display: "flex", flexDirection: "column",
                 }}>
              {p.highlight && (
                <div style={{ textAlign: "center", marginBottom: 12 }}>
                  <span className="badge gradient-text" style={{
                    background: "rgba(34,211,238,.1)", borderColor: "rgba(34,211,238,.25)",
                    fontSize: "0.7rem", fontWeight: 700,
                  }}>
                    ◈ En Popüler
                  </span>
                </div>
              )}
              <div style={{ textAlign: "center", marginBottom: 24 }}>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text2)", marginBottom: 8,
                              textTransform: "uppercase", letterSpacing: "0.1em" }}>
                  {p.tier}
                </h3>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "center", gap: 2 }}>
                  <span style={{ fontSize: "2.4rem", fontWeight: 900, color: "var(--text)" }}>{p.price}</span>
                  <span style={{ fontSize: "0.85rem", color: "var(--text3)" }}>{p.period}</span>
                </div>
              </div>
              <ul style={{ listStyle: "none", padding: 0, marginBottom: 24, flex: 1, display: "flex",
                            flexDirection: "column", gap: 10 }}>
                {p.features.map((feat) => (
                  <li key={feat} style={{ display: "flex", gap: 10, fontSize: "0.85rem", color: "var(--text2)" }}>
                    <span style={{ color: "var(--pos)", flexShrink: 0 }}>✓</span>
                    {feat}
                  </li>
                ))}
              </ul>
              <Link href={p.href} className={p.highlight ? "btn-primary" : "btn-secondary"}
                    style={{ textAlign: "center", textDecoration: "none", justifyContent: "center" }}>
                {p.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid var(--border)", padding: "24px 20px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", justifyContent: "space-between",
                      alignItems: "center", flexWrap: "wrap", gap: 16 }}>
          <span style={{ fontSize: "0.82rem", color: "var(--text3)" }}>
            © 2026 <span className="gradient-text" style={{ fontWeight: 700 }}>NexStream</span>
          </span>
          <div style={{ display: "flex", gap: 24 }}>
            {[
              { label: "Dashboard", href: "/dashboard" },
              { label: "API Docs",  href: "http://localhost:8000/docs" },
              { label: "RSS",       href: "http://localhost:8000/feed.xml" },
            ].map((l) => (
              <a key={l.label} href={l.href} target={l.href.startsWith("http") ? "_blank" : "_self"}
                 style={{ fontSize: "0.82rem", color: "var(--text3)", textDecoration: "none", transition: "color 0.15s" }}
                 onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
                 onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text3)")}>
                {l.label}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
