// 1. Kanca (gürültü) + 2. logo açılışı. İki sahne aynı başlık alanını paylaşır: kancada
// uçuşan başlıklar donar, logo sahnesinde merkeze çekilip logoya dönüşür.

import type React from "react";
import { AbsoluteFill, Easing, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { INTER } from "../fonts";
import { localBeat, SCENES } from "../timeline";
import { ACCENT, usePromo } from "../components/context";
import { NIcon, Wordmark } from "../components/Logo";
import { Sfx } from "../components/Overlay";

const CHIPS = 34;
const FREEZE = 104; // kancada başlıkların donduğu kare

interface Chip { text: string; x: number; y: number; z: number; dir: number; speed: number; appear: number }

function useChips(): Chip[] {
  const { copy, spec } = usePromo();
  return Array.from({ length: CHIPS }, (_, i) => ({
    text: copy.hookHeadlines[i % copy.hookHeadlines.length],
    x: random(`x${i}`) * spec.width * 1.2 - spec.width * 0.1,
    y: (i / CHIPS) * spec.height * 0.92 + random(`y${i}`) * spec.height * 0.06,
    z: 0.45 + random(`z${i}`) * 1.0,
    dir: random(`d${i}`) > 0.5 ? 1 : -1,
    speed: 40 + random(`s${i}`) * 90,
    appear: Math.floor(random(`a${i}`) * 70),
  }));
}

/** Başlığın kancadaki konumu (t: kare). Zaman ilerledikçe hızlanır. */
function chipPos(c: Chip, t: number, width: number) {
  const tt = Math.min(t, FREEZE) / 30;
  const dx = c.dir * c.speed * c.z * (tt + 0.9 * tt * tt);
  const span = width * 1.4;
  const x = ((((c.x + dx + width * 0.2) % span) + span) % span) - width * 0.2;
  return { x, y: c.y };
}

const ChipView: React.FC<{ c: Chip; x: number; y: number; opacity: number; scale?: number; blur?: number; gray?: number }> = ({ c, x, y, opacity, scale = 1, blur = 0, gray = 0 }) => {
  const { spec } = usePromo();
  const fs = spec.hook.headline * c.z;
  return (
    <div style={{
      position: "absolute", left: x, top: y, transform: `translate(-50%, -50%) scale(${scale})`, opacity,
      padding: `${fs * 0.4}px ${fs * 0.7}px`, borderRadius: fs, whiteSpace: "nowrap",
      background: "rgba(255,255,255,.07)", border: "1px solid rgba(255,255,255,.16)", backdropFilter: "blur(4px)",
      color: "#f2ece2", fontFamily: INTER, fontWeight: 600, fontSize: fs,
      filter: `blur(${Math.max(0, (1 - c.z) * 3 + blur)}px) grayscale(${gray})`,
    }}>
      <span style={{ display: "inline-block", width: fs * 0.42, height: fs * 0.42, borderRadius: "50%", background: ACCENT, marginRight: fs * 0.45, verticalAlign: "middle" }} />
      {c.text}
    </div>
  );
};

const Backdrop: React.FC<{ glow?: number }> = ({ glow = 1 }) => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, rgba(120,18,26,${0.55 * glow}) 0%, #0b0606 55%, #040303 100%)` }} />
);

export const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { copy, spec } = usePromo();
  const chips = useChips();
  const frozen = frame >= FREEZE;
  const jitter = frozen ? (random(`j${frame}`) - 0.5) * 10 : 0;
  const t1 = spring({ frame: frame - 8, fps, config: { damping: 16 } });
  const t2 = spring({ frame: frame - 50, fps, config: { damping: 14 } });
  return (
    <AbsoluteFill>
      <Backdrop glow={0.6 + 0.4 * (frame / 120)} />
      <AbsoluteFill style={{ transform: `translateX(${jitter}px)` }}>
        {chips.map((c, i) => {
          const p = chipPos(c, frame, spec.width);
          const o = interpolate(frame - c.appear, [0, 10], [0, 0.9], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return <ChipView key={i} c={c} x={p.x} y={p.y} opacity={o} gray={frozen ? 0.8 : 0} />;
        })}
      </AbsoluteFill>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", padding: 60 }}>
        <div style={{
          fontFamily: INTER, fontWeight: 900, fontSize: spec.hook.title, color: "#fff", letterSpacing: "-0.035em", lineHeight: 1.05,
          textShadow: "0 8px 40px rgba(0,0,0,.8)", opacity: t1, transform: `translateY(${(1 - t1) * 30}px)`,
          background: "rgba(8,5,5,.55)", padding: "10px 28px", borderRadius: 18,
        }}>
          {copy.hook[0]}
        </div>
        <div style={{
          marginTop: 24, fontFamily: INTER, fontWeight: 800, fontSize: spec.hook.title * 0.62, color: "#ff6b75", letterSpacing: "-0.02em",
          textShadow: "0 6px 30px rgba(0,0,0,.9)", opacity: t2, transform: `translateY(${(1 - t2) * 24}px) scale(${frozen ? 1.04 : 1})`,
          background: "rgba(8,5,5,.55)", padding: "8px 24px", borderRadius: 16,
        }}>
          {copy.hook[1]}
        </div>
      </AbsoluteFill>
      <Sfx at={2} name="riser" volume={0.75} />
      <Sfx at={FREEZE} name="flick" volume={0.8} />
    </AbsoluteFill>
  );
};

export const LogoReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { copy, spec } = usePromo();
  const chips = useChips();
  const beat = (n: number) => localBeat(SCENES.logo.fromBeat, n);
  const L = spec.logo;

  const suck = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp", easing: Easing.in(Easing.cubic) });
  const flash = interpolate(frame, [8, 11, 22], [0, 0.9, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const icon = spring({ frame: frame - 7, fps, config: { damping: 11, stiffness: 140 } });
  const word = spring({ frame: frame - beat(1.5), fps, config: { damping: 18, stiffness: 120 } });
  const [s1, s2] = copy.slogan.split(/(?<=\.)\s/);
  const sl1 = spring({ frame: frame - beat(3), fps, config: { damping: 16 } });
  const sl2 = spring({ frame: frame - beat(4), fps, config: { damping: 16 } });

  // son 12 kare: N ikonunun içine dalış → temalar (Matrix) sahnesi
  const diveStart = durationInFrames - 12;
  const dive = interpolate(frame, [diveStart, durationInFrames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.exp) });
  const zoom = 1 + dive * 19;
  const rest = 1 - Math.min(1, dive * 3);

  const cx = spec.width / 2;
  const cy = spec.height / 2;
  const row = L.direction === "row";
  return (
    <AbsoluteFill>
      <Backdrop glow={1 - suck * 0.4} />
      {suck < 1 && chips.map((c, i) => {
        const p = chipPos(c, FREEZE, spec.width);
        return <ChipView key={i} c={c} x={p.x + (cx - p.x) * suck} y={p.y + (cy - p.y) * suck} opacity={0.9 * (1 - suck)} scale={1 - suck * 0.8} blur={suck * 6} gray={0.8} />;
      })}
      <AbsoluteFill style={{ background: `rgba(255,255,255,${flash})` }} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
          <div style={{ display: "flex", flexDirection: L.direction, alignItems: "center", gap: row ? 44 : 40 }}>
            <NIcon size={L.icon} glow={0.6 + 0.4 * Math.sin(frame / 9)} style={{ position: "relative", zIndex: 2, transform: `scale(${icon * zoom}) rotate(${(1 - icon) * -20}deg)` }} />
            <div style={{ overflow: "hidden", paddingBottom: 12, opacity: rest }}>
              <Wordmark size={L.word} style={{ display: "inline-block", transform: `translate${row ? "X" : "Y"}(${(1 - word) * (row ? -60 : 50)}%)`, opacity: word }} />
            </div>
          </div>
          <div style={{ marginTop: row ? 46 : 70, textAlign: "center", opacity: rest, fontFamily: INTER, fontSize: L.slogan, letterSpacing: "-0.015em", lineHeight: 1.3 }}>
            <span style={{ display: row ? "inline-block" : "block", color: "#f6f1e7", fontWeight: 800, opacity: sl1, transform: `translateY(${(1 - sl1) * 20}px)` }}>{s1}</span>
            {row && " "}
            <span style={{ display: row ? "inline-block" : "block", color: "#ff6b75", fontWeight: 800, opacity: sl2, transform: `translateY(${(1 - sl2) * 20}px)` }}>{s2}</span>
          </div>
        </div>
      </AbsoluteFill>
      <Sfx at={0} name="impact" volume={0.9} />
      <Sfx at={beat(1.5)} name="swoosh" volume={0.5} />
      <Sfx at={diveStart} name="whoosh" volume={0.8} />
    </AbsoluteFill>
  );
};
