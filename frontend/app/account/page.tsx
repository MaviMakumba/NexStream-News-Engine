"use client";

// Hesap sayfası: profil + plan, kullanım & kota paneli (v1.11),
// kişisel API anahtarı yönetimi (v1.11) ve plan yükseltme.
// Billing dev modda (BILLING_DEV_MODE=true) yükseltme Stripe'a gitmeden
// anında uygulanır ve kullanıcı bilgisi tazelenir.

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { Navbar } from "@/components/Navbar";
import { TierBadge } from "@/components/TierBadge";
import { AuthLoadingScreen } from "@/components/AuthLoadingScreen";
import { EmailVerifyBanner } from "@/components/EmailVerifyBanner";
import {
  BASE, createCheckout, devDowngrade, fetchBillingConfig, fetchMyUsage,
  generateApiKey, getBillingPortal, revokeApiKey,
} from "@/lib/api";
import type { AccountUsage, BillingConfig } from "@/lib/types";
import { UI, TIER_DETAILS } from "@/lib/i18n";

export default function AccountPage() {
  const { user, isLoading, refreshUser } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];
  const router = useRouter();

  const [usage, setUsage] = useState<AccountUsage | null>(null);
  const [billing, setBilling] = useState<BillingConfig | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [keyBusy, setKeyBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!isLoading && !user) router.replace("/auth/login");
  }, [isLoading, user, router]);

  const loadUsage = useCallback(() => {
    if (!user) return;
    fetchMyUsage(7).then(setUsage).catch(() => {});
  }, [user]);

  useEffect(() => {
    loadUsage();
    fetchBillingConfig().then(setBilling).catch(() => {});
  }, [loadUsage]);

  if (isLoading) return <AuthLoadingScreen />;
  if (!user) return null;

  const info = TIER_DETAILS[lang][user.tier] ?? TIER_DETAILS[lang].free;
  const devMode = billing?.dev_mode ?? false;

  async function handleUpgrade(tier: "pro" | "enterprise") {
    if (!user) return;
    try {
      const res = await createCheckout(tier, window.location.href, window.location.href);
      if (res.dev_mode) {
        // Dev mode: ödeme yok — tier anında değişti, UI'ı tazele.
        await refreshUser();
        loadUsage();
        setNotice(t.devUpgraded);
      } else {
        window.location.href = res.url;  // Stripe Checkout'a yönlendir
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : t.errorOccurred);
    }
  }

  async function handleDowngrade() {
    if (!user) return;
    try {
      await devDowngrade();
      await refreshUser();
      loadUsage();
      setNotice(t.devDowngraded);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : t.errorOccurred);
    }
  }

  async function handlePortal() {
    if (!user) return;
    try {
      const { url } = await getBillingPortal();
      window.location.href = url;
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : t.errorOccurred);
    }
  }

  async function handleGenerateKey() {
    if (!user) return;
    setKeyBusy(true);
    try {
      const { api_key } = await generateApiKey();
      setApiKey(api_key);
      setCopied(false);
      loadUsage();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : t.errorOccurred);
    } finally {
      setKeyBusy(false);
    }
  }

  async function handleRevokeKey() {
    if (!user) return;
    setKeyBusy(true);
    try {
      await revokeApiKey();
      setApiKey(null);
      loadUsage();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : t.errorOccurred);
    } finally {
      setKeyBusy(false);
    }
  }

  function handleCopy() {
    if (!apiKey) return;
    navigator.clipboard.writeText(apiKey).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  const initial = (user.name || user.email || "?")[0].toUpperCase();
  const hasKey = apiKey != null || (usage?.has_api_key ?? false);

  // Kota çubuğu: limit yoksa (Enterprise) gösterilmez.
  const quotaPct = usage?.daily_limit
    ? Math.min(100, Math.round((usage.used_today / usage.daily_limit) * 100))
    : null;

  const quickLinks = [
    { label: t.dashboard, href: "/dashboard" },
    { label: t.search,    href: "/dashboard/search" },
    // Admin linkleri moderator+admin rolüne görünür (v1.13)
    ...(user.is_moderator ? [
      { label: t.users,    href: "/admin/users" },
      { label: t.usage,    href: "/admin/usage" },
      { label: t.sponsors, href: "/admin/sponsors" },
    ] : []),
    { label: t.apiDocs,   href: `${BASE}/docs` },
    { label: t.rssFeed,   href: `${BASE}/feed.xml` },
  ];

  return (
    <div style={{ minHeight: "100vh" }}>
      <Navbar />
      <div style={{ maxWidth: 680, margin: "0 auto", padding: "40px 20px", display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <p className="section-label" style={{ marginBottom: 6 }}>{t.accountLabel}</p>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text)" }}>{t.accountTitle}</h1>
        </div>

        <EmailVerifyBanner />

        {notice && (
          <div style={{ background: "var(--pos-bg)", border: "1px solid var(--pos)", borderRadius: 12,
                        padding: "12px 16px", fontSize: "0.84rem", color: "var(--pos)" }}>
            ✓ {notice}
          </div>
        )}

        {/* Profile */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
            <div style={{
              width: 56, height: 56, borderRadius: "50%", flexShrink: 0,
              background: "linear-gradient(135deg, var(--accent), var(--accent2))",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "1.4rem", fontWeight: 800, color: "#fff", boxShadow: "0 0 20px var(--glow)",
            }}>
              {initial}
            </div>
            <div>
              <div style={{ fontWeight: 700, color: "var(--text)", fontSize: "1rem" }}>{user.name || "—"}</div>
              <div style={{ color: "var(--text3)", fontSize: "0.84rem" }}>{user.email}</div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12, paddingTop: 20,
                        borderTop: "1px solid var(--border)" }}>
            <div>
              <div className="section-label" style={{ marginBottom: 6 }}>{t.planLabel}</div>
              <TierBadge tier={user.tier} lang={lang} />
            </div>
            <div>
              <div className="section-label" style={{ marginBottom: 6 }}>{t.apiLimitLabel}</div>
              <div style={{ fontSize: "0.9rem", color: "var(--text)", fontWeight: 600 }}>{info.limit}</div>
            </div>
          </div>

          <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
            <div className="section-label" style={{ marginBottom: 10 }}>{t.includedFeatures}</div>
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

        {/* Usage & quota (v1.11) */}
        {usage && (
          <div className="card">
            <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text)", marginBottom: 14 }}>
              ◈ {t.usageTitle}
            </h2>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12, marginBottom: 14 }}>
              {[
                { label: t.usedToday,       value: usage.used_today.toLocaleString() },
                { label: t.remainingToday,  value: usage.remaining_today == null ? "∞" : usage.remaining_today.toLocaleString() },
                { label: t.dailyLimitLabel, value: usage.daily_limit == null ? t.unlimited : usage.daily_limit.toLocaleString() },
              ].map((kpi) => (
                <div key={kpi.label} style={{ textAlign: "center", padding: "10px 4px",
                                              background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 10 }}>
                  <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--accent)" }}>{kpi.value}</div>
                  <div className="section-label" style={{ marginTop: 2 }}>{kpi.label}</div>
                </div>
              ))}
            </div>

            {quotaPct != null && (
              <div style={{ marginBottom: 14 }}>
                <div style={{ height: 8, borderRadius: 4, background: "var(--border)", overflow: "hidden" }}>
                  <div style={{
                    height: "100%", width: `${quotaPct}%`, transition: "width 0.4s",
                    background: quotaPct >= 90 ? "var(--neg)" : "linear-gradient(90deg, var(--accent), var(--accent2))",
                  }} />
                </div>
                <div style={{ fontSize: "0.72rem", color: "var(--text3)", marginTop: 4, textAlign: "right" }}>
                  %{quotaPct}
                </div>
              </div>
            )}

            {usage.by_endpoint.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {usage.by_endpoint.map((r) => (
                  <div key={r.endpoint} style={{ display: "flex", justifyContent: "space-between",
                                                 fontSize: "0.8rem", fontFamily: "monospace" }}>
                    <span style={{ color: "var(--accent)" }}>{r.endpoint}</span>
                    <span style={{ color: "var(--text2)" }}>{r.count} · {r.avg_ms.toFixed(0)}ms</span>
                  </div>
                ))}
                <div style={{ fontSize: "0.74rem", color: "var(--text3)", marginTop: 4 }}>
                  {usage.total_requests} {t.windowTotal}
                </div>
              </div>
            ) : (
              <p style={{ fontSize: "0.8rem", color: "var(--text3)" }}>{t.noUsage}</p>
            )}
          </div>
        )}

        {/* API key (v1.11) */}
        <div className="card">
          <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
            ⬡ {t.apiKeyTitle}
          </h2>
          <p style={{ fontSize: "0.84rem", color: "var(--text2)", marginBottom: 14, lineHeight: 1.6 }}>
            {t.apiKeyDesc}
          </p>

          {apiKey ? (
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
              <code style={{
                flex: "1 1 260px", padding: "10px 12px", fontSize: "0.8rem",
                background: "var(--bg)", border: "1px solid var(--accent-line)",
                borderRadius: 8, color: "var(--accent)", wordBreak: "break-all",
              }}>
                {apiKey}
              </code>
              <button onClick={handleCopy} className="btn-secondary" style={{ fontSize: "0.78rem", padding: "8px 14px" }}>
                {copied ? t.copied : t.copyKey}
              </button>
            </div>
          ) : (
            !hasKey && (
              <p style={{ fontSize: "0.8rem", color: "var(--text3)", marginBottom: 12 }}>{t.noApiKey}</p>
            )
          )}

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button onClick={handleGenerateKey} disabled={keyBusy} className="btn-primary"
                    style={{ fontSize: "0.82rem" }}>
              {hasKey ? t.regenerateKey : t.generateKey}
            </button>
            {hasKey && (
              <button onClick={handleRevokeKey} disabled={keyBusy} className="btn-danger"
                      style={{ fontSize: "0.82rem", padding: "8px 16px" }}>
                {t.revokeKey}
              </button>
            )}
          </div>
        </div>

        {/* Upgrade / billing */}
        {user.tier === "free" ? (
          <div className="gradient-border" style={{
            borderRadius: "var(--radius)", padding: 24,
            background: "var(--surface)", backdropFilter: "blur(14px)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text)" }}>
                {t.upgradeTitle}
              </h2>
              {devMode && (
                <span className="badge" style={{ background: "var(--accent-soft)", color: "var(--accent)",
                                                  borderColor: "var(--accent-line)", fontSize: "0.65rem" }}>
                  {t.devModeBadge}
                </span>
              )}
            </div>
            <p style={{ fontSize: "0.84rem", color: "var(--text2)", marginBottom: 16, lineHeight: 1.6 }}>
              {t.upgradeDesc}
            </p>
            {user.email_verified ? (
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button onClick={() => handleUpgrade("pro")} className="btn-primary">{t.proCta}</button>
                <button onClick={() => handleUpgrade("enterprise")} className="btn-secondary">{t.entCta}</button>
              </div>
            ) : (
              <p style={{ fontSize: "0.8rem", color: "var(--neu)" }}>{t.upgradeNeedsVerification}</p>
            )}
          </div>
        ) : (
          <div className="card">
            <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
              {t.billingTitle}
            </h2>
            <p style={{ fontSize: "0.84rem", color: "var(--text2)", marginBottom: 16 }}>{t.billingDesc}</p>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {/* Dev modda Stripe portalı yoktur — simüle düşürme butonu gösterilir */}
              {devMode ? (
                <button onClick={handleDowngrade} className="btn-secondary">{t.devDowngradeBtn}</button>
              ) : (
                <button onClick={handlePortal} className="btn-secondary">{t.billingPortal}</button>
              )}
            </div>
          </div>
        )}

        {/* Quick links */}
        <div className="card">
          <p className="section-label" style={{ marginBottom: 14 }}>{t.quickAccess}</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 8 }}>
            {quickLinks.map((l) => (
              <a key={l.label} href={l.href}
                 target={l.href.startsWith("http") ? "_blank" : "_self"}
                 style={{
                   display: "block", padding: "10px 14px", textAlign: "center",
                   fontSize: "0.82rem", fontWeight: 500, color: "var(--text2)",
                   background: "var(--bg)", border: "1px solid var(--border)",
                   borderRadius: 10, textDecoration: "none", transition: "all 0.15s",
                 }}
                 onMouseEnter={(e) => { const el = e.currentTarget; el.style.borderColor = "var(--accent)"; el.style.color = "var(--accent)"; el.style.background = "var(--accent-soft)"; }}
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
