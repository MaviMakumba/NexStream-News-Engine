"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { useSettings } from "@/lib/settings-context";
import { useAuth } from "@/lib/auth-context";
import { BASE } from "@/lib/api";
import { LandingSearchDemo } from "@/components/LandingSearchDemo";
import { LiveWireStrip } from "@/components/LiveWireStrip";
import { CardSpotlight } from "@/components/CardSpotlight";
import { Footer } from "@/components/Footer";
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

  // "825+" idi — bu bir ölçüm değil, çok eski (v1.11 öncesi) bir hata anındaki
  // ChromaDB indeks sayısıydı, koda sabit yazılmış kalmıştı (18 Ağu 2026'da
  // kullanıcı "bu sayılar ne zamandan kalma" diye sorunca fark edildi). İkisi de
  // public/auth'suz uçlar — kayıt/giriş gerektirmiyor.
  const [liveArticleCount, setLiveArticleCount] = useState<number | null>(null);
  const [liveSourceCount, setLiveSourceCount] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${BASE}/health`)
      .then((r) => r.json())
      .then((d) => typeof d.indexed_articles === "number" && setLiveArticleCount(d.indexed_articles))
      .catch(() => {});
    fetch(`${BASE}/news/sources`)
      .then((r) => r.json())
      .then((d) => Array.isArray(d) && setLiveSourceCount(d.length))
      .catch(() => {});
  }, []);

  const formattedArticles = liveArticleCount != null
    ? `${liveArticleCount.toLocaleString(lang === "TR" ? "tr-TR" : "en-US")}+`
    : "—";

  const stats = [
    { value: formattedArticles, label: t.statArticles },
    { value: liveSourceCount ?? "—", label: t.statSources },
    { value: "<2s",  label: t.statSpeed },
    { value: "100%", label: t.statFree },
  ];

  return (
    <div style={{ minHeight: "100vh" }}>
      <Navbar />

      {/* Hero — sol: manşet + CTA, sağ: GERÇEK verilerle beslenen canlı akış
          (LiveWireStrip) — ürünün "sürekli canlı besleme" farkını süsle değil
          fonksiyonla gösteriyor (18 Eylül 2026 yenileme). auto-fit grid: dar
          ekranda tek sütuna düşer, sabit bir breakpoint gerekmez (Features/
          Pricing bölümleriyle aynı, kanıtlanmış desen). */}
      <section style={{ padding: "72px 20px 64px" }}>
        <div style={{
          maxWidth: 1180, margin: "0 auto", display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 48, alignItems: "center",
        }}>
          <div>
            <h1 style={{
              fontSize: "clamp(2.3rem, 5.4vw, 3.7rem)", fontWeight: 700, lineHeight: 1.12,
              marginBottom: 20, color: "var(--text)", textWrap: "balance" as any,
            }}>
              {t.heroPre}
              <span style={{ color: "var(--accent)" }}>{t.heroAccent}</span>
              {t.heroPost}
            </h1>

            <p style={{
              fontFamily: "var(--font-body)", fontSize: "1.08rem", color: "var(--text2)",
              maxWidth: "46ch", marginBottom: 36, lineHeight: 1.65,
            }}>
              {t.heroSub}
            </p>

            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 44 }}>
              <Link href={primaryHref} className="btn-primary" style={{ fontSize: "0.95rem", padding: "11px 28px" }}>
                {primaryLabel}
              </Link>
              {/* Kayıt/giriş gerektirmez — sayfanın altındaki canlı arama demosuna kaydırır.
                  Önceden ikisi de /dashboard'a gidiyordu (giriş yapmış kullanıcıda hem
                  birincil hem ikincil buton aynı yere), "Demo Görüntüle" fiilen "Panele
                  Git"in kopyasıydı — 18 Ağu 2026'da kullanıcı bulgusu. */}
              <a href="#demo" className="btn-secondary" style={{ fontSize: "0.95rem", padding: "11px 28px" }}>
                {t.ctaSecondary}
              </a>
            </div>

            <div style={{ display: "flex", gap: 36, flexWrap: "wrap" }}>
              {stats.map((s) => (
                // Sabit minWidth: TR/EN etiket uzunlukları farklı (örn. "Haber İndekslendi"
                // vs "Articles Indexed") — genişlik içeriğe göre belirlenirse dil değişince
                // her sütun farklı boy alır ve tüm satır kayar. Her ikisi de bu genişliğe sığar.
                <div key={s.label} style={{ minWidth: 120 }}>
                  <div className="font-display" style={{ fontSize: "1.7rem", fontWeight: 700, lineHeight: 1, color: "var(--accent)" }}>
                    {s.value}
                  </div>
                  <div style={{ fontSize: "0.74rem", color: "var(--text3)", marginTop: 5 }}>
                    {s.label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <LiveWireStrip />
        </div>
      </section>

      {/* "Bir haber kartında neler var" — kullanıcıların Kaydet/güvenilirlik
          skoru/Sor'u fark etmediği geri bildirimi üzerine eklendi (18 Eylül
          2026). Gerçek bir kartın statik kopyası + numaralı pin'ler. */}
      <section style={{ maxWidth: 1100, margin: "0 auto", padding: "16px 20px 72px" }}>
        <h2 style={{ fontSize: "1.7rem", fontWeight: 700, color: "var(--text)", marginBottom: 10 }}>
          {t.spotlightTitle}
        </h2>
        <p style={{ fontFamily: "var(--font-body)", fontSize: "0.92rem", color: "var(--text3)",
                     marginBottom: 32, maxWidth: "60ch" }}>
          {t.spotlightIntro}
        </p>
        <CardSpotlight />
      </section>

      {/* Canlı arama demosu — kayıt olmadan denenebilir */}
      <section id="demo" style={{ padding: "0 20px 80px", scrollMarginTop: 80 }}>
        <p style={{ textAlign: "center", fontFamily: "var(--font-body)", fontSize: "0.86rem",
                     color: "var(--text3)", marginBottom: 18 }}>
          {t.landingSearchConnector}
        </p>
        <LandingSearchDemo />
      </section>

      {/* Features */}
      <section style={{ maxWidth: 1100, margin: "0 auto", padding: "60px 20px" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <p className="section-label" style={{ marginBottom: 10 }}>{t.featuresLabel}</p>
          <h2 style={{ fontSize: "1.9rem", fontWeight: 800, color: "var(--text)" }}>{t.featuresTitle}</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
          {features.map((f) => {
            const body = (
              <>
                <div style={{
                  width: 46, height: 46, borderRadius: 12, marginBottom: 16,
                  background: "var(--accent-soft)", border: "1px solid var(--accent-line)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "1.35rem", color: f.accent,
                }}>
                  {f.icon}
                </div>
                <h3 style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "1.05rem",
                              fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
                  {f.title}
                  {f.badge && (
                    <span className="badge" style={{ background: "var(--accent-soft)", color: "var(--accent)",
                                                      borderColor: "var(--accent-line)", fontSize: "0.6rem" }}>
                      {f.badge}
                    </span>
                  )}
                </h3>
                <p style={{ fontSize: "0.875rem", color: "var(--text2)", lineHeight: 1.65 }}>{f.desc}</p>
              </>
            );
            // Bülten/Export/İletişim gerçek bir hedefe gidiyor (/account,
            // /contact) — kullanıcı bunları "sadece anlatmakla kalmayıp
            // faydalanabilsinler" istedi, o yüzden tıklanabilir (18 Eylül
            // 2026). İlk üç özellik tek bir sayfa değil, tüm deneyime yayılan
            // davranışlar — onlar statik kart olarak kalıyor.
            return f.href ? (
              <Link key={f.title} href={f.href} className="card" style={{ textDecoration: "none", display: "block" }}>
                {body}
              </Link>
            ) : (
              <div key={f.title} className="card">{body}</div>
            );
          })}
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

      <Footer />
    </div>
  );
}
