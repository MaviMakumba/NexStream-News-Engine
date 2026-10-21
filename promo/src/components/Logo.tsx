// Marka: sekmede görünen yeşil "N" uygulama ikonu (frontend/public/icons/icon-512.png'nin
// vektör karşılığı — büyük boyda bulanıklaşmasın) + sitenin "NexStream" yazısı (Newsreader).

import type React from "react";
import { INTER, NEWSREADER } from "../fonts";

export const N_GREEN = "#2bff9e";

export const NIcon: React.FC<{ size: number; glow?: number; style?: React.CSSProperties }> = ({ size, glow = 0.6, style }) => (
  <div style={{
    width: size, height: size, borderRadius: size * 0.22, flexShrink: 0,
    background: "radial-gradient(circle at 30% 25%, #0b1f16 0%, #030a07 70%)",
    boxShadow: `0 0 ${size * 0.5}px rgba(43,255,158,${0.35 * glow}), inset 0 0 0 ${Math.max(2, size * 0.012)}px rgba(43,255,158,.25)`,
    display: "flex", alignItems: "center", justifyContent: "center", ...style,
  }}>
    <span style={{
      fontFamily: INTER, fontWeight: 800, fontSize: size * 0.62, lineHeight: 1, color: N_GREEN,
      textShadow: `0 0 ${size * 0.12}px rgba(43,255,158,${0.8 * glow})`, transform: `translateY(${size * 0.01}px)`,
    }}>
      N
    </span>
  </div>
);

export const Wordmark: React.FC<{ size: number; dark?: boolean; style?: React.CSSProperties }> = ({ size, dark = true, style }) => (
  <span style={{ fontFamily: NEWSREADER, fontWeight: 800, fontSize: size, letterSpacing: "-0.02em", lineHeight: 1, whiteSpace: "nowrap", ...style }}>
    <span style={{ color: dark ? "#f6f1e7" : "#1c1a16" }}>Nex</span>
    <span style={{
      background: dark ? "linear-gradient(120deg, #ff4b57, #c31e2a)" : "linear-gradient(120deg, #c31e2a, #8f1620)",
      WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent",
    }}>
      Stream
    </span>
  </span>
);
