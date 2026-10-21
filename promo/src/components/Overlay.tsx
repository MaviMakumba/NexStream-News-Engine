// Ekran (kare) koordinatında çizilen katmanlar: vurgu halkası + etiket, alt yazı,
// imleç, yazma imleci, ses efekti.

import type React from "react";
import { Easing, Html5Audio, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { type Cam, projectRect } from "../camera";
import type { Rect } from "../manifest";
import { INTER } from "../fonts";
import { ACCENT, usePromo } from "./context";

/** 0→1→0 görünürlük: [from, to) aralığında, `fade` karede girip çıkar. */
export function visibility(frame: number, from: number, to: number, fade = 6) {
  if (frame < from || frame >= to) return 0;
  return Math.min(1, (frame - from) / fade, (to - frame) / fade);
}

export type Side = "top" | "bottom" | "left" | "right";

/** Sayfadaki bir dikdörtgeni halkayla çevirip yanına etiket koyar. */
export const Callout: React.FC<{ rect: Rect; cam: Cam; text?: string; from: number; to: number; side?: Side; pad?: number; gap?: number }> = ({ rect, cam, text, from, to, side = "top", pad = 7, gap = 30 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { view, spec } = usePromo();
  if (frame < from || frame >= to) return null;
  const pop = spring({ frame: frame - from, fps, config: { damping: 14, stiffness: 180 } });
  const out = interpolate(frame, [to - 6, to], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const r = projectRect(view, cam, rect);
  const ring = { x: r.x - pad, y: r.y - pad, w: r.w + pad * 2, h: r.h + pad * 2 };
  const fs = spec.label.fontSize;
  const estW = text ? text.length * fs * 0.56 + fs * 1.4 : 0;
  const estH = fs * 1.9;
  let lx = ring.x;
  let ly = ring.y - gap - estH;
  if (side === "bottom") ly = ring.y + ring.h + gap;
  if (side === "left") { lx = ring.x - gap - estW; ly = ring.y + ring.h / 2 - estH / 2; }
  if (side === "right") { lx = ring.x + ring.w + gap; ly = ring.y + ring.h / 2 - estH / 2; }
  lx = Math.max(24, Math.min(view.W - estW - 24, lx));
  ly = Math.max(24, Math.min(view.H - estH - 24, ly));
  // bağlantı çizgisi: halka kenarından etiketin en yakın noktasına
  const anchor = side === "top" ? { x: Math.min(Math.max(ring.x + 28, lx + 20), lx + estW - 20), y: ring.y } :
    side === "bottom" ? { x: Math.min(Math.max(ring.x + 28, lx + 20), lx + estW - 20), y: ring.y + ring.h } :
    side === "left" ? { x: ring.x, y: ring.y + ring.h / 2 } : { x: ring.x + ring.w, y: ring.y + ring.h / 2 };
  const target = side === "top" ? { x: anchor.x, y: ly + estH } : side === "bottom" ? { x: anchor.x, y: ly } :
    side === "left" ? { x: lx + estW, y: anchor.y } : { x: lx, y: anchor.y };
  const len = Math.hypot(target.x - anchor.x, target.y - anchor.y);
  const ang = Math.atan2(target.y - anchor.y, target.x - anchor.x);
  return (
    <div style={{ position: "absolute", inset: 0, opacity: out, pointerEvents: "none" }}>
      <div style={{
        position: "absolute", left: ring.x, top: ring.y, width: ring.w, height: ring.h, borderRadius: 12,
        border: `4px solid ${ACCENT}`, boxShadow: `0 0 0 6px rgba(195,30,42,.18), 0 0 28px rgba(195,30,42,.35)`,
        opacity: pop, transform: `scale(${1.12 - 0.12 * pop})`,
      }} />
      {text && (
        <>
          <div style={{
            position: "absolute", left: anchor.x, top: anchor.y, width: len * pop, height: 3, background: ACCENT,
            transformOrigin: "0 50%", transform: `rotate(${ang}rad)`,
          }} />
          <div style={{
            position: "absolute", left: lx, top: ly, height: estH, display: "flex", alignItems: "center",
            padding: `0 ${fs * 0.7}px`, borderRadius: estH / 2, background: ACCENT, color: "#fff",
            fontFamily: INTER, fontWeight: 800, fontSize: fs, letterSpacing: "-0.01em", whiteSpace: "nowrap",
            boxShadow: "0 10px 30px rgba(0,0,0,.35)",
            opacity: pop, transform: `translateY(${(1 - pop) * 14}px) scale(${0.9 + 0.1 * pop})`,
          }}>
            {text}
          </div>
        </>
      )}
    </div>
  );
};

/** Sahne alt yazısı: kelimeler sırayla yükselerek girer. Yerel karelerle çalışır. */
export const Caption: React.FC<{ text: string; from: number; to: number; dark?: boolean }> = ({ text, from, to, dark = true }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { spec } = usePromo();
  if (frame < from || frame >= to) return null;
  const c = spec.caption;
  const out = interpolate(frame, [to - 8, to], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const words = text.split(" ");
  const plateIn = spring({ frame: frame - from, fps, config: { damping: 20, stiffness: 160 } });
  const top = c.top !== null;
  return (
    <>
    {/* alt yazının arkasındaki karartma bandı: altına giren içerik geri plana çekilir */}
    <div style={{
      position: "absolute", left: 0, right: 0, height: top ? c.top! + c.fontSize * 5 : (c.bottom ?? 0) + c.fontSize * 4,
      top: top ? 0 : undefined, bottom: top ? undefined : 0, opacity: out * plateIn * (dark ? 1 : 0),
      background: `linear-gradient(${top ? "180deg" : "0deg"}, rgba(10,8,7,.55), rgba(10,8,7,0))`,
    }} />
    <div style={{
      position: "absolute", left: c.align === "center" ? (spec.width - c.maxWidth) / 2 : c.side, top: c.top ?? undefined,
      bottom: c.bottom ?? undefined, width: c.maxWidth, display: "flex", justifyContent: c.align === "center" ? "center" : "flex-start",
      opacity: out, transform: `translateY(${(1 - out) * 16}px)`,
    }}>
      <div style={{
        display: "inline-block", padding: `${c.fontSize * 0.36}px ${c.fontSize * 0.55}px`, borderRadius: 20,
        background: dark ? "rgba(16,12,10,.80)" : "rgba(255,255,255,.86)", backdropFilter: "blur(14px)",
        borderLeft: c.align === "left" ? `7px solid ${ACCENT}` : undefined, borderBottom: c.align === "center" ? `6px solid ${ACCENT}` : undefined,
        boxShadow: "0 18px 50px rgba(0,0,0,.35)", transform: `scale(${0.96 + 0.04 * plateIn})`, opacity: plateIn,
        textAlign: c.align, lineHeight: 1.15,
      }}>
        {words.map((w, i) => {
          const p = spring({ frame: frame - from - 3 - i * 2, fps, config: { damping: 18, stiffness: 200 } });
          return (
            <span key={i} style={{
              display: "inline-block", marginRight: i < words.length - 1 ? "0.26em" : 0,
              fontFamily: INTER, fontWeight: 800, fontSize: c.fontSize, letterSpacing: "-0.02em", color: dark ? "#fff" : "#14110e",
              opacity: p, transform: `translateY(${(1 - p) * 0.5}em)`,
            }}>
              {w}
            </span>
          );
        })}
      </div>
    </div>
    </>
  );
};

export interface PathKey { f: number; x: number; y: number }

/** Sayfa koordinatında yol: anahtar kareler arası yumuşak geçiş. */
export function pathAt(frame: number, keys: PathKey[]) {
  if (frame <= keys[0].f) return keys[0];
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1];
    const b = keys[i];
    if (frame <= b.f) {
      const t = interpolate(frame, [a.f, b.f], [0, 1], { easing: Easing.inOut(Easing.cubic) });
      return { f: frame, x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
    }
  }
  return keys[keys.length - 1];
}

/** İmleç (masaüstü ok) ya da dokunma noktası (mobil). x,y kare koordinatı. */
export const Cursor: React.FC<{ x: number; y: number; clicks: number[]; opacity?: number }> = ({ x, y, clicks, opacity = 1 }) => {
  const frame = useCurrentFrame();
  const { spec } = usePromo();
  const last = clicks.filter((c) => c <= frame).pop();
  const since = last === undefined ? 99 : frame - last;
  const press = since < 6 ? interpolate(since, [0, 2, 6], [1, 0.82, 1]) : 1;
  const ripple = since < 14 ? since / 14 : null;
  const touch = spec.cursor === "touch";
  return (
    <div style={{ position: "absolute", left: 0, top: 0, opacity, pointerEvents: "none" }}>
      {ripple !== null && (
        <div style={{
          position: "absolute", left: x - 60 * ripple, top: y - 60 * ripple, width: 120 * ripple, height: 120 * ripple, borderRadius: "50%",
          border: `4px solid ${ACCENT}`, opacity: 1 - ripple,
        }} />
      )}
      {touch ? (
        <div style={{
          position: "absolute", left: x - 34, top: y - 34, width: 68, height: 68, borderRadius: "50%",
          background: "rgba(255,255,255,.55)", border: "3px solid rgba(20,17,14,.55)", boxShadow: "0 6px 20px rgba(0,0,0,.35)",
          transform: `scale(${press})`,
        }} />
      ) : (
        <svg width={44} height={52} viewBox="0 0 22 26" style={{ position: "absolute", left: x - 4, top: y - 2, transform: `scale(${press})`, transformOrigin: "4px 2px", filter: "drop-shadow(0 4px 6px rgba(0,0,0,.4))" }}>
          <path d="M2 1 L2 20 L7 15.5 L10.5 23.5 L13.8 22 L10.3 14.2 L17 14.2 Z" fill="#fff" stroke="#14110e" strokeWidth="1.6" strokeLinejoin="round" />
        </svg>
      )}
    </div>
  );
};

/** Yazma imleci (ekran koordinatı). */
export const Caret: React.FC<{ x: number; y: number; h: number; color?: string }> = ({ x, y, h, color = "#14110e" }) => {
  const frame = useCurrentFrame();
  const on = Math.floor(frame / 8) % 2 === 0;
  return <div style={{ position: "absolute", left: x, top: y, width: 3, height: h, background: color, opacity: on ? 1 : 0.15 }} />;
};

/** Yerel `from` karesinde bir ses efekti. */
export const Sfx: React.FC<{ at: number; name: string; volume?: number }> = ({ at, name, volume = 1 }) => (
  <Sequence from={Math.round(at)} durationInFrames={90} layout="none">
    <Html5Audio src={staticFile(`sfx/${name}.wav`)} volume={volume} />
  </Sequence>
);

/** Yazma animasyonu için ilerleme: [from, to) içinde 0→1, karakter adımlı. */
export function typed(frame: number, from: number, to: number, chars: number) {
  const p = interpolate(frame, [from, to], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return Math.round(p * chars) / Math.max(1, chars);
}
