"use client";

// Anasayfa hero'sunun sağ paneli — ürünün asıl farkını (sürekli canlı
// besleme) süs olarak değil GERÇEK veriyle gösterir (18 Eylül 2026 yenileme).
//
// Gerçek WebSocket canlı akışı (/ws/feed, bkz. useLiveFeed.ts) Pro-özel —
// anonim ziyaretçide "kilitli" ekranı gösterirdi, bu da pazarlama sayfasının
// tam anlatmaya çalıştığı şeyi (ürünün ne yaptığını) baştan kilitlerdi. Onun
// yerine tamamen public olan /feed.xml'i periyodik çekiyoruz (footer'daki
// "RSS" linkiyle aynı uç) — dürüst, kota/oturum gerektirmez.

import { useEffect, useRef, useState } from "react";
import { BASE } from "@/lib/api";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

interface WireItem {
  id: string;
  title: string;
  url: string;
  source: string;
}

const POLL_MS = 45_000;
const MAX_ITEMS = 5;

function parseFeed(xml: string): WireItem[] {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  if (doc.querySelector("parsererror")) return [];
  return Array.from(doc.querySelectorAll("item"))
    .slice(0, MAX_ITEMS)
    .map((item, i) => ({
      id: item.querySelector("guid")?.textContent || item.querySelector("link")?.textContent || String(i),
      title: item.querySelector("title")?.textContent?.trim() || "",
      url: item.querySelector("link")?.textContent?.trim() || "#",
      source: item.querySelector("category")?.textContent?.trim() || "",
    }))
    .filter((it) => it.title);
}

export function LiveWireStrip() {
  const { lang } = useSettings();
  const t = UI[lang];
  const [items, setItems] = useState<WireItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    async function load() {
      try {
        const res = await fetch(`${BASE}/feed.xml`);
        if (!res.ok) throw new Error(String(res.status));
        const xml = await res.text();
        const parsed = parseFeed(xml);
        if (mountedRef.current && parsed.length > 0) {
          setItems(parsed);
          setFailed(false);
        }
      } catch {
        if (mountedRef.current && items === null) setFailed(true);
      }
    }
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      mountedRef.current = false;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "12px 16px", borderBottom: "1px solid var(--border)",
      }}>
        <span style={{
          width: 7, height: 7, borderRadius: "50%", background: "var(--accent)",
          boxShadow: "0 0 8px var(--accent)",
          animation: "glow-pulse 1.8s ease-in-out infinite", flexShrink: 0,
        }} />
        <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--text)" }}>
          {t.liveWireLabel}
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column" }}>
        {items === null && !failed && (
          <div style={{ padding: "14px 16px", fontSize: "0.82rem", color: "var(--text3)" }}>
            {t.loadingShort}
          </div>
        )}
        {failed && items === null && (
          <div style={{ padding: "14px 16px", fontSize: "0.82rem", color: "var(--text3)" }}>
            {t.liveWireError}
          </div>
        )}
        {items?.length === 0 && (
          <div style={{ padding: "14px 16px", fontSize: "0.82rem", color: "var(--text3)" }}>
            {t.liveWireEmpty}
          </div>
        )}
        {items?.map((it, i) => (
          <a key={it.id} href={it.url} target="_blank" rel="noopener noreferrer"
             className={i === 0 ? "animate-fade-in" : undefined}
             style={{
               display: "block", padding: "11px 16px", textDecoration: "none",
               borderBottom: i < items.length - 1 ? "1px solid var(--border)" : "none",
               transition: "background 0.15s",
             }}
             onMouseEnter={(e) => (e.currentTarget.style.background = "var(--accent-soft)")}
             onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
            {it.source && (
              <div style={{ fontSize: "0.66rem", fontWeight: 700, color: "var(--accent)",
                            marginBottom: 3, letterSpacing: "0.02em" }}>
                {it.source}
              </div>
            )}
            <div style={{
              fontSize: "0.84rem", color: "var(--text2)", lineHeight: 1.4,
              display: "-webkit-box" as any, WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any,
              overflow: "hidden",
            }}>
              {it.title}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
