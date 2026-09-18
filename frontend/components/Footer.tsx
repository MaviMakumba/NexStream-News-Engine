"use client";

// Paylaşılan footer — 18 Eylül 2026'ya kadar sadece anasayfada (page.tsx
// içine gömülü) vardı, kullanıcı bulgusu: /privacy, /terms, /contact gibi
// arama motorundan doğrudan gelinebilecek public sayfalarda site keşfi için
// hiçbir yol yoktu. Bilinçli olarak dashboard/hesabım/admin gibi giriş
// gerektiren "app" sayfalarına EKLENMEDİ — yoğun/işlevsel ekranlarda footer
// eklemek çoğu profesyonel SaaS'ta (Gmail, Notion, Linear) yapılmayan bir
// şey, gereksiz kalabalık.

import { BASE } from "@/lib/api";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

export function Footer() {
  const { lang } = useSettings();
  const t = UI[lang];

  return (
    <footer style={{ borderTop: "1px solid var(--border)", padding: "24px 20px" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", justifyContent: "space-between",
                    alignItems: "center", flexWrap: "wrap", gap: 16 }}>
        <span style={{ fontSize: "0.82rem", color: "var(--text3)" }}>
          © 2026 <span style={{ fontWeight: 700, color: "var(--accent)" }}>NexStream</span> — {t.footerTagline}
        </span>
        {/* flexWrap: dar ekranda 7 link tek satıra sığmıyordu, body'deki
            global overflow-x:hidden taşan kısmı sayfa kaydırmasına
            çevirmek yerine kırpıyordu (18 Eylül 2026). */}
        <div style={{ display: "flex", gap: "10px 24px", flexWrap: "wrap" }}>
          {[
            { label: t.dashboard, href: "/dashboard" },
            { label: t.apiDocs,   href: `${BASE}/docs` },
            { label: "RSS",       href: `${BASE}/feed.xml` },
            { label: t.privacy,   href: "/privacy" },
            { label: t.terms,     href: "/terms" },
            { label: t.security,  href: "/security" },
            { label: t.contactLink, href: "/contact" },
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
  );
}
