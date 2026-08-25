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
import { NewsCard } from "@/components/NewsCard";
import { PushNotificationToggle } from "@/components/PushNotificationToggle";
import {
  BASE, createCheckout, deleteAccount, devDowngrade, downloadExport, fetchBillingConfig, fetchMyNewsletter, fetchMyUsage,
  fetchSavedArticles, fetchSources, generateApiKey, getBillingPortal, revokeApiKey, saveNewsletter, unsubscribeNewsletter,
} from "@/lib/api";
import type { AccountUsage, Article, BillingConfig, Tier } from "@/lib/types";
import type { NewsletterPrefs } from "@/lib/api";
import { UI, TIER_DETAILS, TOPIC_LABELS } from "@/lib/i18n";

const NEWSLETTER_TOPICS = ["Technology", "Sports", "Economy", "Politics", "Health", "Culture", "World", "Other"];
const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";

export default function AccountPage() {
  const { user, isLoading, refreshUser, logout } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];
  const router = useRouter();

  const [usage, setUsage] = useState<AccountUsage | null>(null);
  const [billing, setBilling] = useState<BillingConfig | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [keyBusy, setKeyBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [notice, setNotice] = useState("");
  const [exportFormat, setExportFormat] = useState<"csv" | "json">("csv");
  const [exportBusy, setExportBusy] = useState(false);

  // Kaydedilenler (bookmarks, v2.2)
  const [saved, setSaved] = useState<Article[] | null>(null);

  // Hesap silme (v2.1.2) — danger zone
  const [delOpen, setDelOpen] = useState(false);
  const [delPassword, setDelPassword] = useState("");
  const [delConfirmed, setDelConfirmed] = useState(false);
  const [delBusy, setDelBusy] = useState(false);
  const [delError, setDelError] = useState("");

  // Bülten tercihleri (v2.1.1) — backend zaten hazırdı, hesap sayfasında hiç
  // UI'ı yoktu (kullanıcı gerçek hesabında abone kaydı olmadığını fark edince
  // ortaya çıktı — bkz. CLAUDE.md/CHANGELOG).
  const [sources, setSources] = useState<string[]>([]);
  const [nlFrequency, setNlFrequency] = useState<"daily" | "instant" | "never">("never");
  const [nlTopics, setNlTopics] = useState<string[]>([]);
  const [nlSources, setNlSources] = useState<string[]>([]);
  const [nlKeywords, setNlKeywords] = useState("");
  const [nlBusy, setNlBusy] = useState(false);
  const [nlSaved, setNlSaved] = useState(false);
  const [nlSubscribed, setNlSubscribed] = useState(false);

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
    fetchSources().then(setSources).catch(() => {});
    fetchSavedArticles().then(setSaved).catch(() => {});
    fetchMyNewsletter().then((prefs: NewsletterPrefs) => {
      setNlSubscribed(prefs.subscribed);
      if (prefs.subscribed) {
        setNlFrequency(prefs.frequency ?? "daily");
        setNlTopics(prefs.preferred_topics ?? []);
        setNlSources(prefs.preferred_sources ?? []);
        setNlKeywords((prefs.keywords ?? []).join(", "));
      }
    }).catch(() => {});
  }, [loadUsage]);

  if (isLoading) return <AuthLoadingScreen />;
  if (!user) return null;

  const info = TIER_DETAILS[lang][user.effective_tier ?? user.tier] ?? TIER_DETAILS[lang].free;
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

  function toggleNlTopic(topic: string) {
    setNlSaved(false);
    setNlTopics((cur) => (cur.includes(topic) ? cur.filter((x) => x !== topic) : [...cur, topic]));
  }

  function toggleNlSource(source: string) {
    setNlSaved(false);
    setNlSources((cur) => (cur.includes(source) ? cur.filter((x) => x !== source) : [...cur, source]));
  }

  async function handleSaveNewsletter() {
    if (!user) return;
    setNlBusy(true);
    setNlSaved(false);
    try {
      await saveNewsletter(user.email, {
        frequency: nlFrequency,
        keywords: nlKeywords.split(",").map((k) => k.trim()).filter(Boolean),
        preferred_sources: nlSources,
        preferred_topics: nlTopics,
        language: lang,
      });
      setNlSubscribed(nlFrequency !== "never");
      setNlSaved(true);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : t.errorOccurred);
    } finally {
      setNlBusy(false);
    }
  }

  async function handleUnsubscribeNewsletter() {
    if (!user) return;
    setNlBusy(true);
    try {
      await unsubscribeNewsletter(user.email);
      setNlSubscribed(false);
      setNlFrequency("never");
      setNlSaved(false);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : t.errorOccurred);
    } finally {
      setNlBusy(false);
    }
  }

  async function handleExport() {
    setExportBusy(true);
    try {
      await downloadExport(exportFormat);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : t.errorOccurred);
    } finally {
      setExportBusy(false);
    }
  }

  async function handleDeleteAccount() {
    if (!delConfirmed || !delPassword) return;
    setDelBusy(true);
    setDelError("");
    try {
      await deleteAccount(delPassword);
      await logout();
      router.replace("/");
    } catch (err: unknown) {
      setDelError(err instanceof Error ? err.message : t.errorOccurred);
    } finally {
      setDelBusy(false);
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
              <TierBadge tier={(user.effective_tier ?? user.tier) as Tier} lang={lang} isOwner={user.is_owner} />
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

        {/* Kaydedilenler (bookmarks, v2.2) */}
        <div className="card">
          <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
            🔖 {t.savedPageTitle}
          </h2>
          <p style={{ fontSize: "0.84rem", color: "var(--text2)", marginBottom: 16, lineHeight: 1.6 }}>
            {t.savedPageDesc}
          </p>
          {saved === null ? (
            <p style={{ fontSize: "0.8rem", color: "var(--text3)" }}>{t.loading}</p>
          ) : saved.length === 0 ? (
            <p style={{ fontSize: "0.8rem", color: "var(--text3)" }}>{t.savedEmpty}</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {saved.map((a) => <NewsCard key={a.id} article={a} />)}
            </div>
          )}
        </div>

        {/* Bülten tercihleri (v2.1.1) */}
        <div className="card">
          <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
            ✉ {t.newsletterTitle}
          </h2>
          <p style={{ fontSize: "0.84rem", color: "var(--text2)", marginBottom: 6, lineHeight: 1.6 }}>
            {t.newsletterDesc}
          </p>
          <p style={{ fontSize: "0.78rem", color: nlSubscribed ? "var(--accent)" : "var(--text3)", marginBottom: 16 }}>
            {nlSubscribed ? t.newsletterSubscribedNote : t.newsletterNotSubscribedNote}
          </p>

          <div style={{ marginBottom: 14 }}>
            <span className="section-label" style={{ display: "block", marginBottom: 8 }}>{t.newsletterFreqLabel}</span>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {([
                ["daily", t.newsletterFreqDaily, true],
                ["instant", t.newsletterFreqInstant, (user.effective_tier ?? user.tier) !== "free"],
                ["never", t.newsletterFreqNever, true],
              ] as [typeof nlFrequency, string, boolean][]).map(([value, label, enabled]) => (
                <button key={value} type="button"
                  onClick={() => { if (enabled) { setNlFrequency(value); setNlSaved(false); } }}
                  disabled={!enabled}
                  title={!enabled ? t.newsletterFreqInstantLocked : undefined}
                  className={nlFrequency === value ? "btn-primary" : "btn-secondary"}
                  style={{ fontSize: "0.78rem", padding: "7px 14px", opacity: enabled ? 1 : 0.45,
                           cursor: enabled ? "pointer" : "not-allowed" }}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: 14 }}>
            <span className="section-label" style={{ display: "block", marginBottom: 8 }}>{t.newsletterTopicsLabel}</span>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {NEWSLETTER_TOPICS.map((topic) => (
                <button key={topic} type="button" onClick={() => toggleNlTopic(topic)}
                  className="badge" style={{
                    cursor: "pointer", fontSize: "0.75rem",
                    background: nlTopics.includes(topic) ? "var(--accent-soft)" : "var(--surface)",
                    color: nlTopics.includes(topic) ? "var(--accent)" : "var(--text3)",
                    borderColor: nlTopics.includes(topic) ? "var(--accent-line)" : "var(--border)",
                  }}>
                  {TOPIC_LABELS[lang][topic] ?? topic}
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: 14 }}>
            <span className="section-label" style={{ display: "block", marginBottom: 8 }}>{t.newsletterSourcesLabel}</span>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {sources.map((source) => (
                <button key={source} type="button" onClick={() => toggleNlSource(source)}
                  className="badge" style={{
                    cursor: "pointer", fontSize: "0.75rem",
                    background: nlSources.includes(source) ? "var(--accent-soft)" : "var(--surface)",
                    color: nlSources.includes(source) ? "var(--accent)" : "var(--text3)",
                    borderColor: nlSources.includes(source) ? "var(--accent-line)" : "var(--border)",
                  }}>
                  {source}
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: 18 }}>
            <span className="section-label" style={{ display: "block", marginBottom: 8 }}>{t.newsletterKeywordsLabel}</span>
            <input type="text" value={nlKeywords}
              onChange={(e) => { setNlKeywords(e.target.value); setNlSaved(false); }}
              placeholder={t.newsletterKeywordsPlaceholder}
              style={{
                width: "100%", padding: "9px 12px", fontSize: "0.84rem", borderRadius: 8,
                background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)",
              }} />
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button onClick={handleSaveNewsletter} disabled={nlBusy} className="btn-primary" style={{ fontSize: "0.82rem" }}>
              {nlSaved ? t.newsletterSaved : t.newsletterSave}
            </button>
            {nlSubscribed && (
              <button onClick={handleUnsubscribeNewsletter} disabled={nlBusy} className="btn-danger"
                      style={{ fontSize: "0.82rem", padding: "8px 16px" }}>
                {t.newsletterUnsubscribe}
              </button>
            )}
          </div>

          <PushNotificationToggle
            vapidPublicKey={VAPID_PUBLIC_KEY}
            enabled={nlFrequency === "instant" && (user.effective_tier ?? user.tier) !== "free"}
            lockedReason={t.pushLockedReason}
            label={t.pushLabel}
            subscribedLabel={t.pushSubscribedLabel}
            errorLabel={t.pushErrorLabel}
          />
        </div>

        {/* Ham veri export (v1.16, Enterprise) */}
        {(user.effective_tier ?? user.tier) === "enterprise" && (
          <div className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text)" }}>
                ⇩ {t.exportTitle}
              </h2>
              <span className="badge" style={{ background: "var(--accent-soft)", color: "var(--accent)",
                                                borderColor: "var(--accent-line)", fontSize: "0.65rem" }}>
                {t.exportBadge}
              </span>
            </div>
            <p style={{ fontSize: "0.84rem", color: "var(--text2)", marginBottom: 16, lineHeight: 1.6 }}>
              {t.exportDesc}
            </p>
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 10 }}>
              <span className="section-label">{t.exportFormatLabel}</span>
              <div style={{ display: "flex", gap: 6 }}>
                {(["csv", "json"] as const).map((f) => (
                  <button key={f} onClick={() => setExportFormat(f)}
                          aria-pressed={exportFormat === f}
                          className={exportFormat === f ? "btn-primary" : "btn-secondary"}
                          style={{ fontSize: "0.78rem", padding: "6px 14px", textTransform: "uppercase" }}>
                    {f}
                  </button>
                ))}
              </div>
              <button onClick={handleExport} disabled={exportBusy} className="btn-primary"
                      style={{ fontSize: "0.82rem" }}>
                {exportBusy ? t.loading2 : `⇩ ${t.exportDownloadBtn}`}
              </button>
            </div>
            <p style={{ fontSize: "0.74rem", color: "var(--text3)" }}>{t.exportRowCapNote}</p>
          </div>
        )}

        {/* Upgrade / billing — owner'a hiç gösterilmez, satın alınacak/yönetilecek bir şeyi yok */}
        {!user.is_owner && (
          user.tier === "free" ? (
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
          )
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

        {/* Tehlikeli bölge — hesap silme (v2.1.2) */}
        <div className="card" style={{ borderColor: "var(--neg)" }}>
          <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--neg)", marginBottom: 8 }}>
            ⚠ {t.dangerZoneTitle}
          </h2>
          <p style={{ fontSize: "0.84rem", color: "var(--text2)", marginBottom: 16, lineHeight: 1.6 }}>
            {t.dangerZoneDesc}
          </p>
          {user.is_owner ? (
            <p style={{ fontSize: "0.8rem", color: "var(--text3)" }}>{t.deleteAccountOwnerNote}</p>
          ) : !delOpen ? (
            <button onClick={() => setDelOpen(true)} className="btn-danger"
                    style={{ fontSize: "0.82rem", padding: "8px 16px" }}>
              {t.deleteAccountBtn}
            </button>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 360 }}>
              <p style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text)" }}>{t.deleteAccountConfirmTitle}</p>
              <div>
                <label className="label">{t.deleteAccountPasswordLabel}</label>
                <input type="password" value={delPassword}
                       onChange={(e) => setDelPassword(e.target.value)}
                       className="input" autoComplete="current-password" />
              </div>
              <label style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: "0.82rem", color: "var(--text2)", cursor: "pointer" }}>
                <input type="checkbox" checked={delConfirmed}
                       onChange={(e) => setDelConfirmed(e.target.checked)}
                       style={{ marginTop: 2 }} />
                {t.deleteAccountCheckboxLabel}
              </label>
              {delError && (
                <div style={{ background: "var(--neg-bg)", border: "1px solid var(--neg)", borderRadius: 10,
                              padding: "8px 12px", fontSize: "0.8rem", color: "var(--neg)" }}>⚠ {delError}</div>
              )}
              <div style={{ display: "flex", gap: 10 }}>
                <button onClick={handleDeleteAccount}
                        disabled={delBusy || !delConfirmed || !delPassword}
                        className="btn-danger" style={{ fontSize: "0.82rem", padding: "8px 16px" }}>
                  {delBusy ? t.deleteAccountSubmitting : t.deleteAccountSubmit}
                </button>
                <button onClick={() => { setDelOpen(false); setDelPassword(""); setDelConfirmed(false); setDelError(""); }}
                        disabled={delBusy} className="btn-secondary" style={{ fontSize: "0.82rem", padding: "8px 16px" }}>
                  {t.deleteAccountCancel}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
