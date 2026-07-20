"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, isLoading } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];

  const tabs = [
    { href: "/admin/users",    icon: "◉", label: t.users },
    { href: "/admin/usage",    icon: "◈", label: t.usage },
    { href: "/admin/sponsors", icon: "⬡", label: t.sponsors },
  ];

  // Giriş yapmış ama moderator/admin OLMAYAN kullanıcıya "API anahtarı gir"
  // demek yanlış (anahtarı yok, olmamalı da) — açık bir 403 göster. API key
  // girişi sadece OTURUMSUZ (anonim/makine) erişim için sayfa içinde kalır.
  const forbidden = !isLoading && Boolean(user) && !user?.is_moderator;

  return (
    <div style={{ minHeight: "100vh" }}>
      <Navbar />
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 20px" }}>
        <div style={{ marginBottom: 28 }}>
          <p className="section-label" style={{ marginBottom: 6 }}>{t.admin}</p>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text)", marginBottom: 4 }}>
            {t.adminTitle}
          </h1>
          <p style={{ fontSize: "0.84rem", color: "var(--text3)" }}>{t.adminSub}</p>
        </div>

        {forbidden ? (
          <div className="card" style={{ textAlign: "center", padding: "56px 24px" }}>
            <div style={{ fontSize: "2.4rem", marginBottom: 14, color: "var(--neg)" }}>⛔</div>
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
              403 — {t.accessDenied}
            </h2>
            <p style={{ fontSize: "0.86rem", color: "var(--text3)", marginBottom: 20 }}>
              {t.accessDeniedDesc}
            </p>
            <Link href="/dashboard" className="btn-secondary" style={{ justifyContent: "center" }}>
              {t.dashboard}
            </Link>
          </div>
        ) : (
        <>
        {/* Tabs */}
        <div style={{ display: "flex", gap: 6, marginBottom: 28, padding: 4,
                      background: "var(--surface)", border: "1px solid var(--border)",
                      borderRadius: 12, width: "fit-content",
                      backdropFilter: "blur(12px)" }}>
          {tabs.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link key={tab.href} href={tab.href} style={{
                padding: "7px 18px", borderRadius: 8, fontSize: "0.84rem", fontWeight: 600,
                textDecoration: "none", transition: "all 0.15s",
                display: "flex", alignItems: "center", gap: 6,
                color:      active ? "#fff"             : "var(--text3)",
                background: active ? "var(--accent)"   : "transparent",
                boxShadow:  active ? "0 0 16px var(--glow)" : "none",
              }}>
                <span style={{ fontSize: "0.75rem" }}>{tab.icon}</span>
                {tab.label}
              </Link>
            );
          })}
        </div>

        {children}
        </>
        )}
      </div>
    </div>
  );
}
