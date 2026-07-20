"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useLiveFeed } from "@/lib/useLiveFeed";
import { useSettings } from "@/lib/settings-context";
import { useAuth } from "@/lib/auth-context";
import { UI } from "@/lib/i18n";

const ROTATE_MS = 5000;

export function LiveTicker() {
  const { lang } = useSettings();
  const { user } = useAuth();
  const t = UI[lang];
  const isPro = user?.tier === "pro" || user?.tier === "enterprise";
  const { articles, status } = useLiveFeed(isPro);
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const lastIdRef = useRef<number | null>(null);

  // Yeni haber gelince ticker en başa (en yeniye) döner.
  useEffect(() => {
    const newestId = articles[0]?.id ?? null;
    if (newestId !== null && newestId !== lastIdRef.current) {
      lastIdRef.current = newestId;
      setIndex(0);
    }
  }, [articles]);

  // WCAG 2.2.2 (Pause, Stop, Hide): 5sn'de bir kendiliğinden değişen içerik
  // hover veya klavye focus'unda durur — okumaya çalışan kullanıcı yarıda kesilmesin.
  useEffect(() => {
    if (articles.length < 2 || paused) return;
    const id = setInterval(() => setIndex((i) => (i + 1) % articles.length), ROTATE_MS);
    return () => clearInterval(id);
  }, [articles.length, paused]);

  const dotColor =
    status === "live" ? "var(--pos)" : status === "connecting" ? "var(--text3)" : "var(--neg)";
  const statusLabel =
    status === "live" ? t.liveOn : status === "connecting" ? t.liveConnecting : t.liveOff;
  const current = articles[index];

  // Free tier: hiç bağlanmayı denemeyiz (bkz. useLiveFeed enabled param) —
  // sonsuz reconnect döngüsü yerine doğrudan yükseltme çağrısı gösteririz.
  if (status === "locked") {
    return (
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "8px 20px", borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
      }}>
        <span style={{ fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.08em",
                       color: "var(--text3)", textTransform: "uppercase", flexShrink: 0 }}>
          ◆ {t.liveOn}
        </span>
        <span style={{ fontSize: "0.82rem", color: "var(--text3)", flex: 1 }}>
          {t.liveLocked}
        </span>
        <Link href="/account" className="btn-secondary"
              style={{ fontSize: "0.72rem", padding: "4px 12px", flexShrink: 0 }}>
          {t.liveUpgrade}
        </Link>
      </div>
    );
  }

  return (
    <div
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      style={{
        display: "flex", alignItems: "center", gap: 12,
        padding: "8px 20px", borderBottom: "1px solid var(--border)",
        background: "var(--surface)", overflow: "hidden",
      }}>
      <span style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
        <span style={{
          width: 7, height: 7, borderRadius: "50%", background: dotColor,
          animation: status === "live" ? "glow-pulse 1.6s ease-in-out infinite" : undefined,
          opacity: status === "connecting" ? 0.6 : 1,
        }} />
        <span style={{
          fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.08em",
          color: "var(--text3)", textTransform: "uppercase", whiteSpace: "nowrap",
        }}>
          {statusLabel}
        </span>
      </span>

      <div style={{ width: 1, height: 14, background: "var(--border)", flexShrink: 0 }} />

      {current ? (
        <a key={current.id} href={current.url} target="_blank" rel="noopener noreferrer"
           className="animate-fade-in"
           style={{
             fontSize: "0.82rem", color: "var(--text2)", textDecoration: "none",
             whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
             flex: 1, transition: "color 0.15s", minWidth: 0,
           }}
           onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent)")}
           onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text2)")}>
          <span style={{ color: "var(--accent)", fontWeight: 700, marginRight: 6 }}>
            {current.source}
          </span>
          {current.title}
        </a>
      ) : (
        <span style={{ fontSize: "0.82rem", color: "var(--text3)", flex: 1 }}>{t.liveWaiting}</span>
      )}

      {articles.length > 1 && (
        <span style={{ fontSize: "0.68rem", color: "var(--text3)", flexShrink: 0 }}>
          {index + 1}/{articles.length}
        </span>
      )}
    </div>
  );
}
