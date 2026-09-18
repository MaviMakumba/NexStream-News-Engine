"use client";

// Anasayfa — "bir haber kartında neler var" bölümü (18 Eylül 2026 yenileme,
// 18 Eylül 2026'da kullanıcı geri bildirimiyle genişletildi: Dinle/İlgili
// haberler/Habere git de eklendi, üst meta satırı — kaynak/haber tipi/duygu
// durumu/anahtar kelimeler — tek bir açıklama cümlesiyle kapsandı, Sor için
// minik bir örnek diyalog eklendi). Gerçek bir kartın statik bir kopyasını
// gösterip her butonu numaralı pin'lerle işaretliyoruz — pin'ler
// işaretledikleri düğmeye/rozete göreceli konumlandığı için (page-wide bir
// bağlantı çizgisi değil) herhangi bir genişlikte kırılmadan çalışır.

import { SentimentBadge } from "./SentimentBadge";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

function Pin({ n }: { n: number }) {
  return (
    <span aria-hidden style={{
      position: "absolute", top: -7, right: -7, width: 18, height: 18,
      borderRadius: "50%", background: "var(--accent)", color: "#fff",
      fontSize: "0.65rem", fontWeight: 800, display: "flex",
      alignItems: "center", justifyContent: "center", flexShrink: 0,
      boxShadow: "0 0 0 2px var(--bg)",
    }}>
      {n}
    </span>
  );
}

export function CardSpotlight() {
  const { lang } = useSettings();
  const t = UI[lang];

  const legend = [
    { n: 1, title: t.spotlightSaveTitle, desc: t.spotlightSaveDesc },
    { n: 2, title: t.spotlightTrustTitle, desc: t.spotlightTrustDesc },
    {
      n: 3, title: t.spotlightAskTitle, desc: t.spotlightAskDesc,
      example: (
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6, maxWidth: 340 }}>
          <div style={{ alignSelf: "flex-end", background: "var(--accent-soft)", borderRadius: 10,
                        padding: "6px 10px", fontSize: "0.78rem", color: "var(--text)" }}>
            {t.spotlightAskExampleQ}
          </div>
          <div style={{ alignSelf: "flex-start", background: "var(--surface)", border: "1px solid var(--border)",
                        borderRadius: 10, padding: "6px 10px", fontSize: "0.78rem", color: "var(--text2)" }}>
            {t.spotlightAskExampleA}
          </div>
        </div>
      ),
    },
    { n: 4, title: t.spotlightListenTitle, desc: t.spotlightListenDesc },
    { n: 5, title: t.spotlightRelatedTitle, desc: t.spotlightRelatedDesc },
    { n: 6, title: t.spotlightGoTitle, desc: t.spotlightGoDesc },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 32, alignItems: "start" }}>
      {/* Mockup kart — gerçek NewsCard ile aynı görsel dil, statik/etkileşimsiz */}
      <div>
        <article className="card" aria-hidden style={{ cursor: "default" }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", marginBottom: 10 }}>
            <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--accent)",
                           textTransform: "uppercase", letterSpacing: "0.06em" }}>
              {t.spotlightMockSource}
            </span>
            <span style={{ color: "var(--border2)", fontSize: "0.65rem" }}>•</span>
            <span style={{ fontSize: "0.72rem", color: "var(--text3)" }}>2{lang === "TR" ? "sa" : "h"}</span>
            <span className="badge" style={{ background: "rgba(0,0,0,.06)", color: "var(--text3)", borderColor: "var(--border)" }}>
              {t.spotlightMockTopic}
            </span>
            <SentimentBadge label="Neutral" />
            <span style={{ marginLeft: "auto", position: "relative", display: "inline-block" }}>
              <span className="badge" style={{ background: "rgba(0,0,0,.06)", color: "var(--text3)", borderColor: "var(--border)" }}>
                ✦ 82
              </span>
              <Pin n={2} />
            </span>
          </div>

          <div style={{ color: "var(--text)", fontWeight: 700, fontSize: "0.95rem", lineHeight: 1.45 }}>
            {t.spotlightMockTitle}
          </div>

          <p style={{ marginTop: 8, fontSize: "0.84rem", color: "var(--text2)", lineHeight: 1.6 }}>
            {t.spotlightMockSummary}
          </p>

          <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 5 }}>
            {[t.spotlightMockEntity1, t.spotlightMockEntity2, t.spotlightMockEntity3].map((e) => (
              <span key={e} className="badge" style={{
                background: "var(--accent-soft)", color: "var(--accent)",
                borderColor: "var(--accent-line)", fontSize: "0.68rem",
              }}>
                {e}
              </span>
            ))}
          </div>

          <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)",
                        display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span style={{ position: "relative", display: "inline-flex" }}>
              <span className="icon-chip">
                <span className="icon-chip-glyph">↗</span> {t.related}
              </span>
              <Pin n={5} />
            </span>
            <span style={{ position: "relative", display: "inline-flex" }}>
              <span className="icon-chip">
                <span className="icon-chip-glyph">💬</span> {t.askCardButton}
              </span>
              <Pin n={3} />
            </span>
            <span style={{ position: "relative", display: "inline-flex" }}>
              <span className="icon-chip icon-chip--iconOnly">
                <span className="icon-chip-glyph">🔊</span>
              </span>
              <Pin n={4} />
            </span>
            <span style={{ position: "relative", display: "inline-flex" }}>
              <span className="icon-chip icon-chip--iconOnly">
                <span className="icon-chip-glyph">🏷</span>
              </span>
              <Pin n={1} />
            </span>
            <span style={{ position: "relative", display: "inline-flex", marginLeft: "auto" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text3)" }}>{t.goToArticle}</span>
              <Pin n={6} />
            </span>
          </div>
        </article>

        <p style={{ marginTop: 14, fontSize: "0.82rem", color: "var(--text3)", lineHeight: 1.6 }}>
          {t.spotlightMetaLine}
        </p>
      </div>

      {/* Legend */}
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        {legend.map((l) => (
          <div key={l.n} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
            <span style={{
              width: 24, height: 24, borderRadius: "50%", background: "var(--accent)",
              color: "#fff", fontSize: "0.75rem", fontWeight: 800, flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center", marginTop: 2,
            }}>
              {l.n}
            </span>
            <div>
              <div style={{ fontWeight: 700, color: "var(--text)", fontSize: "0.95rem", marginBottom: 3 }}>
                {l.title}
              </div>
              <p style={{ fontSize: "0.86rem", color: "var(--text2)", lineHeight: 1.6, maxWidth: "60ch" }}>
                {l.desc}
              </p>
              {"example" in l && l.example}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
