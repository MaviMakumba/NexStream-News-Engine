"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { Navbar } from "@/components/Navbar";
import { TierBadge } from "@/components/TierBadge";
import { createCheckout, getBillingPortal } from "@/lib/api";

const TIER_INFO = {
  free:       { limit: "100 istek / gün",    icon: "○", color: "#94a3b8",  features: ["Haberler & arama", "10 arama sonucu", "Günlük digest e-posta"] },
  pro:        { limit: "2.000 istek / gün",  icon: "◈", color: "#22d3ee",  features: ["Tüm Ücretsiz özellikler", "WebSocket canlı akış", "50 arama sonucu", "İlişki grafı"] },
  enterprise: { limit: "Sınırsız",           icon: "◆", color: "#a78bfa",  features: ["Tüm Pro özellikler", "Ham veri export", "Özel kaynak ekleme", "SLA garantisi"] },
} as const;

export default function AccountPage() {
  const { user, token, isLoading } = useAuth();
  const { lang } = useSettings();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !token) router.replace("/auth/login");
  }, [isLoading, token, router]);

  if (isLoading) return null;
  if (!user) return null;

  const info = TIER_INFO[user.tier] ?? TIER_INFO.free;

  async function handleUpgrade(tier: "pro" | "enterprise") {
    if (!token) return;
    try {
      const { url } = await createCheckout(token, tier, window.location.href, window.location.href);
      window.location.href = url;
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Hata oluştu.");
    }
  }

  async function handlePortal() {
    if (!token) return;
    try {
      const { url } = await getBillingPortal(token);
      window.location.href = url;
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Hata oluştu.");
    }
  }

  const initial = (user.name || user.email || "?")[0].toUpperCase();

  return (
    <div style={{ minHeight: "100vh" }}>
      <Navbar />
      <div style={{ maxWidth: 680, margin: "0 auto", padding: "40px 20px", display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <p className="section-label" style={{ marginBottom: 6 }}>Account</p>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text)", letterSpacing: "-0.02em" }}>
            Hesabım
          </h1>
        </div>

        {/* Profile */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
            <div style={{
              width: 56, height: 56, borderRadius: "50%", flexShrink: 0,
              background: "linear-gradient(135deg, var(--accent), var(--accent2))",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "1.4rem", fontWeight: 800, color: "#fff",
              boxShadow: "0 0 20px var(--glow)",
            }}>
              {initial}
            </div>
            <div>
              <div style={{ fontWeight: 700, color: "var(--text)", fontSize: "1rem" }}>
                {user.name || "—"}
              </div>
              <div style={{ color: "var(--text3)", fontSize: "0.84rem" }}>{user.email}</div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, paddingTop: 20,
                        borderTop: "1px solid var(--border)" }}>
            <div>
              <div className="section-label" style={{ marginBottom: 6 }}>Plan</div>
              <TierBadge tier={user.tier} lang={lang} />
            </div>
            <div>
              <div className="section-label" style={{ marginBottom: 6 }}>API Limiti</div>
              <div style={{ fontSize: "0.9rem", color: "var(--text)", fontWeight: 600 }}>{info.limit}</div>
            </div>
          </div>

          <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
            <div className="section-label" style={{ marginBottom: 10 }}>Dahil Özellikler</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {info.features.map((f) => (
                <div key={f} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.84rem", color: "var(--text2)" }}>
                  <span style={{ color: "var(--pos)", fontSize: "0.7rem" }}>✓</span>
                  {f}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Upgrade */}
        {user.tier === "free" && (
          <div className="gradient-border" style={{
            borderRadius: 14, padding: 24,
            background: "var(--surface)", backdropFilter: "blur(14px)",
          }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
              ◈ Pro'ya Yükselt
            </h2>
            <p style={{ fontSize: "0.84rem", color: "var(--text2)", marginBottom: 16, lineHeight: 1.6 }}>
              2.000 istek/gün, WebSocket canlı akış ve daha fazlası — aylık yalnızca $9.99.
            </p>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button onClick={() => handleUpgrade("pro")} className="btn-primary">
                Pro — $9.99/ay
              </button>
              <button onClick={() => handleUpgrade("enterprise")} className="btn-secondary">
                Kurumsal — $49.99/ay
              </button>
            </div>
          </div>
        )}

        {user.tier !== "free" && (
          <div className="card">
            <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
              Fatura Yönetimi
            </h2>
            <p style={{ fontSize: "0.84rem", color: "var(--text2)", marginBottom: 16 }}>
              Aboneliğinizi yönetin, faturalarınıza bakın.
            </p>
            <button onClick={handlePortal} className="btn-secondary">
              Fatura Portalı →
            </button>
          </div>
        )}

        {/* Quick links */}
        <div className="card">
          <p className="section-label" style={{ marginBottom: 14 }}>Hızlı Erişim</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 8 }}>
            {[
              { label: "Haberler",     href: "/dashboard" },
              { label: "Arama",        href: "/dashboard/search" },
              { label: "Kullanım",     href: "/admin/usage" },
              { label: "Sponsorlar",   href: "/admin/sponsors" },
              { label: "API Docs",     href: "http://localhost:8000/docs" },
              { label: "RSS Feed",     href: "http://localhost:8000/feed.xml" },
            ].map((l) => (
              <a key={l.label} href={l.href}
                 target={l.href.startsWith("http") ? "_blank" : "_self"}
                 style={{
                   display: "block", padding: "10px 14px", textAlign: "center",
                   fontSize: "0.82rem", fontWeight: 500, color: "var(--text2)",
                   background: "var(--bg)", border: "1px solid var(--border)",
                   borderRadius: 10, textDecoration: "none", transition: "all 0.15s",
                 }}
                 onMouseEnter={(e) => { const el = e.currentTarget; el.style.borderColor = "var(--accent)"; el.style.color = "var(--accent)"; el.style.background = "rgba(34,211,238,.05)"; }}
                 onMouseLeave={(e) => { const el = e.currentTarget; el.style.borderColor = "var(--border)"; el.style.color = "var(--text2)"; el.style.background = "var(--bg)"; }}>
                {l.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
