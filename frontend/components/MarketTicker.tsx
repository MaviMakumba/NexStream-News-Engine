"use client";

import { useEffect, useState } from "react";
import { fetchMarketSnapshot } from "@/lib/api";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";
import type { MarketQuote, MarketSnapshot } from "@/lib/types";

const POLL_MS = 60_000;

export function MarketTicker() {
  const { lang } = useSettings();
  const t = UI[lang];
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchMarketSnapshot().then((s) => {
        // fetchMarketSnapshot() resolves to null on ANY failure (network blip,
        // a single non-200, etc.) — only overwrite on a real snapshot so a
        // transient failure doesn't blank a ticker the backend went to real
        // effort to keep serving (stale-but-valid fallback, see market_router.py).
        if (!cancelled) setSnapshot((prev) => s ?? prev);
      });
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (!snapshot) return null;

  const locale = lang === "TR" ? "tr-TR" : "en-US";
  const fmt = (n: number, digits = 2) =>
    n.toLocaleString(locale, { minimumFractionDigits: digits, maximumFractionDigits: digits });

  const items: Array<{ label: string; quote: MarketQuote; suffix: string }> = [
    { label: t.marketBist, quote: snapshot.bist100, suffix: "" },
    { label: t.marketUsd, quote: snapshot.usd_try, suffix: " ₺" },
    { label: t.marketEur, quote: snapshot.eur_try, suffix: " ₺" },
    { label: t.marketGold, quote: snapshot.gold_gram_try, suffix: " ₺" },
  ];

  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 18,
        padding: "6px 20px", borderBottom: "1px solid var(--border)",
        background: "var(--surface)", overflowX: "auto",
      }}
    >
      {items.map((item) => {
        const up = item.quote.change_pct >= 0;
        return (
          <div key={item.label} style={{ display: "flex", alignItems: "baseline", gap: 6, flexShrink: 0 }}>
            <span style={{
              fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.04em",
              color: "var(--text3)", textTransform: "uppercase",
            }}>
              {item.label}
            </span>
            <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--text)" }}>
              {fmt(item.quote.value)}{item.suffix}
            </span>
            <span style={{ fontSize: "0.72rem", fontWeight: 700, color: up ? "var(--pos)" : "var(--neg)" }}>
              {up ? "▲" : "▼"} {fmt(Math.abs(item.quote.change_pct))}%
            </span>
          </div>
        );
      })}
      {snapshot.stale && (
        <span style={{ fontSize: "0.68rem", color: "var(--text3)", fontStyle: "italic", flexShrink: 0 }}>
          ({t.marketStale})
        </span>
      )}
    </div>
  );
}
