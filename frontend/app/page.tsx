"use client";

import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { useSettings } from "@/lib/settings-context";
import { useAuth } from "@/lib/auth-context";
import { BASE } from "@/lib/api";
import { LandingSearchDemo } from "@/components/LandingSearchDemo";
import { UI, FEATURES, PRICING } from "@/lib/i18n";

export default function LandingPage() {
  const { lang } = useSettings();
  const { user } = useAuth();
  const t = UI[lang];
  const features = FEATURES[lang];
  const pricing = PRICING[lang];

  // Auth-aware primary CTA: logged-in users go straight to the dashboard.
  const primaryHref = user ? "/dashboard" : "/auth/register";
  const primaryLabel = user ? t.ctaAuthed : t.ctaPrimary;

  const stats = [
    { value: "825+", label: t.statArticles },
    { value: "17",   label: t.statSources },
    { value: "<2s",  label: t.statSpeed },
    { value: "100%", label: t.statFree },
  ];

  return (
    <div style={{ minHeight: "100vh" }}>
      <Navbar />

      {/* Hero — overflow burada (bölüm seviyesinde) clip'lenir; kökte overflowX:hidden
          navbar'ın sticky/scroll-hide davranışını kırıyordu (scroll container'a çeviriyordu). */}
      <section style={{ position: "relative", padding: "100px 20px 80px", textAlign: "center", overflow: "hidden" }}>
        <div className="grid-bg" style={{
          position: "absolute", inset: 0, zIndex: 0, pointerEvents: "none",
          maskImage: "radial-gradient(ellipse 80% 60% at 50% 0%, black, transparent)",
          WebkitMaskImage: "radial-gradient(ellipse 80% 60% at 50% 0%, black, transparent)",
        }} />
        <div style={{
          position: "absolute", top: 0, left: "25%", width: 600, height: 300,
          background: "radial-gradient(ellipse, var(--glow) 0%, transparent 70%)",
          pointerEvents: "none", zIndex: 0,
        }} />
        <div style={{
          position: "absolute", top: 50, right: "15%", width: 400, height: 250,
          background: "radial-gradient(ellipse, var(--glow2) 0%, transparent 70%)",
          pointerEvents: "none", zIndex: 0,
        }} />

        <div style={{ position: "relative", zIndex: 1, maxWidth: 800, margin: "0 auto" }}>
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 8,
            background: "var(--accent-soft)", border: "1px solid var(--accent-line)",
            borderRadius: 9999, padding: "6px 16px", marginBottom: 32, fontSize: "0.8rem",
            color: "var(--accent)",
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: "50%", background: "var(--accent)",
              boxShadow: "0 0 8px var(--accent)",
              animation: "glow-pulse 2s ease-in-out infinite", display: "inline-block",
            }} />
            {t.heroBadge}
          </div>

          <h1 style={{
            fontSize: "clamp(2.4rem, 6vw, 4.2rem)", fontWeight: 900, lineHeight: 1.08,
            marginBottom: 24, color: "var(--text)",
          }}>
            {t.heroPre}
            <span className="gradient-text">{t.heroAccent}</span>
            {t.heroPost}
          </h1>

          <p style={{
            fontSize: "1.1rem", color: "var(--text2)", maxWidth: 540, margin: "0 auto 40px",
            lineHeight: 1.7,
          }}>
            {t.heroSub}
          </p>

          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link href={primaryHref} className="btn-primary" style={{ fontSize: "0.95rem", padding: "11px 28px" }}>
              {primaryLabel}
            </Link>
            <Link href="/dashboard" className="btn-secondary" style={{ fontSize: "0.95rem", padding: "11px 28px" }}>
              {t.ctaSecondary}
            </Link>
          </div>
        </div>

        <div style={{
          position: "relative", zIndex: 1,
          display: "flex", justifyContent: "center", gap: 48, marginTop: 64, flexWrap: "wrap",
        }}>
          {stats.map((s) => (
            // Sabit minWidth: TR/EN etiket uzunlukları farklı (örn. "Haber İndekslendi"
            // vs "Articles Indexed") — genişlik içeriğe göre belirlenirse dil değişince
            // her sütun farklı boy alır ve tüm satır kayar. Her ikisi de bu genişliğe sığar.
            <div key={s.label} style={{ textAlign: "center", minWidth: 160 }}>
              <div className="gradient-text font-display" style={{ fontSize: "1.9rem", fontWeight: 800, lineHeight: 1 }}>
                {s.value}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text3)", marginTop: 6,
                            textTransform: "uppercase", letterSpacing: "0.08em" }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Canlı arama demosu — kayıt olmadan denenebilir */}
      <section style={{ padding: "0 20px 80px" }}>
        <LandingSearchDemo />
      </section>

      {/* Features */}
      <section style={{ maxWidth: 1100, margin: "0 auto", padding: "60px 20px" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <p className="section-label" style={{ marginBottom: 10 }}>{t.featuresLabel}</p>
          <h2 style={{ fontSize: "1.9rem", fontWeight: 800, color: "var(--text)" }}>{t.featuresTitle}</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
          {features.map((f) => (
            <div key={f.title} className="card" style={{ overflow: "hidden" }}>
              <div style={{
                position: "absolute", top: 0, right: 0, width: 150, height: 150,
                background: "radial-gradient(circle, var(--glow), transparent 70%)",
                pointerEvents: "none",
              }} />
              <div style={{
                width: 46, height: 46, borderRadius: 12, marginBottom: 16,
                background: "var(--accent-soft)", border: "1px solid var(--accent-line)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "1.35rem", color: f.accent,
              }}>
                {f.icon}
              </div>
              <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
                {f.title}
              </h3>
              <p style={{ fontSize: "0.875rem", color: "var(--text2)", lineHeight: 1.65 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section style={{ maxWidth: 1100, margin: "0 auto", padding: "40px 20px 80px" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <p className="section-label" style={{ marginBottom: 10 }}>{t.pricingLabel}</p>
          <h2 style={{ fontSize: "1.9rem", fontWeight: 800, color: "var(--text)" }}>{t.pricingTitle}</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 20 }}>
          {pricing.map((p) => (
            <div key={p.tier} className={p.highlight ? "gradient-border" : "card"}
                 style={{
                   ...(p.highlight ? {
                     borderRadius: "var(--radius)", padding: 20,
                     background: "var(--surface)", backdropFilter: "blur(14px)",
                     boxShadow: "0 0 40px var(--glow)",
                   } : {}),
                   display: "flex", flexDirection: "column",
                 }}>
              {p.highlight && (
                <div style={{ textAlign: "center", marginBottom: 12 }}>
                  <span className="badge" style={{
                    background: "var(--accent-soft)", borderColor: "var(--accent-line)",
                    color: "var(--accent)", fontSize: "0.7rem", fontWeight: 700,
                  }}>
                    ◈ {t.mostPopular}
                  </span>
                </div>
              )}
              <div style={{ textAlign: "center", marginBottom: 24 }}>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text2)", marginBottom: 8,
                              textTransform: "uppercase", letterSpacing: "0.1em" }}>
                  {p.tier}
                </h3>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "center", gap: 2 }}>
                  <span className="font-display" style={{ fontSize: "2.4rem", fontWeight: 900, color: "var(--text)" }}>{p.price}</span>
                  <span style={{ fontSize: "0.85rem", color: "var(--text3)" }}>{p.period}</span>
                </div>
              </div>
              <ul style={{ listStyle: "none", padding: 0, marginBottom: 24, flex: 1,
                            display: "flex", flexDirection: "column", gap: 10 }}>
                {p.features.map((feat) => (
                  <li key={feat} style={{ display: "flex", gap: 10, fontSize: "0.85rem", color: "var(--text2)" }}>
                    <span style={{ color: "var(--pos)", flexShrink: 0 }}>✓</span>
                    {feat}
                  </li>
                ))}
              </ul>
              <Link href={user ? "/account" : p.href} className={p.highlight ? "btn-primary" : "btn-secondary"}
                    style={{ textAlign: "center", textDecoration: "none", justifyContent: "center" }}>
                {user ? t.managePlan : p.cta}
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
            © 2026 <span className="gradient-text" style={{ fontWeight: 700 }}>NexStream</span> — {t.footerTagline}
          </span>
          <div style={{ display: "flex", gap: 24 }}>
            {[
              { label: t.dashboard, href: "/dashboard" },
              { label: t.apiDocs,   href: `${BASE}/docs` },
              { label: "RSS",       href: `${BASE}/feed.xml` },
              { label: t.privacy,   href: "/privacy" },
              { label: t.terms,     href: "/terms" },
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
