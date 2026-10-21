"use client";

// Ana sayfa tanıtım videosu (promo/ ile üretilir, bkz. promo/README.md). Kapak + oynat
// butonu: video yalnız tıklanınca iner (sunucu/ziyaretçi bant genişliği). Ziyaretçinin
// diline ve ekranına göre yatay ya da dikey sürüm seçilir. Dosya adındaki sürüm değişince
// tarayıcı/Cloudflare önbelleği kendiliğinden yenilenir.

import { useEffect, useState } from "react";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

const VERSION = "v1";
const LANG_FILE: Record<string, string> = { TR: "tr", EN: "en" };
type Layout = "desktop" | "mobile";

const file = (lang: string, layout: Layout, ext: "mp4" | "jpg") =>
  `/promo/promo-${LANG_FILE[lang] ?? "en"}-${layout}-${VERSION}.${ext}`;

export function PromoVideo() {
  const { lang } = useSettings();
  const t = UI[lang];
  const [layout, setLayout] = useState<Layout>("desktop");
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const apply = () => setLayout(mq.matches ? "mobile" : "desktop");
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  // Dil ya da yerleşim değişince kapağa dön (yanlış sürüm oynamaya devam etmesin).
  useEffect(() => setPlaying(false), [lang, layout]);

  const mobile = layout === "mobile";
  return (
    <section id="tanitim" style={{ padding: "0 20px 72px", scrollMarginTop: 80 }}>
      <div style={{ maxWidth: 980, margin: "0 auto", textAlign: "center" }}>
        <p className="section-label" style={{ marginBottom: 10 }}>{t.promoLabel}</p>
        <h2 style={{ fontSize: "1.7rem", fontWeight: 700, color: "var(--text)", marginBottom: 24 }}>{t.promoTitle}</h2>
        <div style={{
          position: "relative", margin: "0 auto", borderRadius: 16, overflow: "hidden", background: "#000",
          boxShadow: "0 18px 50px rgba(0,0,0,.25)", aspectRatio: mobile ? "9 / 16" : "16 / 9",
          width: mobile ? "min(100%, calc(80dvh * 9 / 16))" : "100%",
        }}>
          {playing ? (
            <video src={file(lang, layout, "mp4")} poster={file(lang, layout, "jpg")} controls autoPlay playsInline
                   style={{ width: "100%", height: "100%", display: "block" }} />
          ) : (
            <button type="button" onClick={() => setPlaying(true)} aria-label={t.promoPlay}
                    style={{ position: "absolute", inset: 0, padding: 0, border: 0, background: "none", cursor: "pointer" }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={file(lang, layout, "jpg")} alt="" style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
              <span aria-hidden style={{
                position: "absolute", left: "50%", top: mobile ? "68%" : "74%", transform: "translate(-50%, -50%)",
                display: "inline-flex", alignItems: "center", gap: 10, padding: "12px 26px", borderRadius: 999,
                background: "var(--accent)", color: "#fff", fontWeight: 700, fontSize: "1rem",
                boxShadow: "0 10px 30px rgba(0,0,0,.35)",
              }}>
                ▶ {t.promoPlay}
              </span>
            </button>
          )}
        </div>
        <p style={{ fontFamily: "var(--font-body)", fontSize: "0.82rem", color: "var(--text3)", marginTop: 12 }}>{t.promoNote}</p>
      </div>
    </section>
  );
}
