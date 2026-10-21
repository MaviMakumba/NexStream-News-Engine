// 10. Kapanış: ayrı sahnesi olmayan özellikler çip çip belirir; müziğin kendi son
// vuruşunda (FINAL_HIT_BEAT) çipler merkeze çekilir → N ikonu + logo + adres + çağrı.

import type React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { INTER } from "../fonts";
import { FINAL_HIT_BEAT, localBeat, SCENES } from "../timeline";
import { ACCENT, usePromo } from "../components/context";
import { NIcon, Wordmark } from "../components/Logo";
import { Sfx } from "../components/Overlay";

export const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { copy, spec } = usePromo();
  const b = (n: number) => localBeat(SCENES.outro.fromBeat, n);
  const hit = b(FINAL_HIT_BEAT - SCENES.outro.fromBeat);
  const chips = copy.outro.chips;
  const row = spec.logo.direction === "row";

  const gather = interpolate(frame, [hit - 6, hit], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.cubic) });
  const lock = spring({ frame: frame - hit, fps, config: { damping: 12, stiffness: 120 } });
  const word = spring({ frame: frame - hit - 5, fps, config: { damping: 16 } });
  const url = spring({ frame: frame - hit - 12, fps, config: { damping: 18 } });
  const cta = spring({ frame: frame - hit - 18, fps, config: { damping: 14 } });
  const flash = interpolate(frame, [hit, hit + 2, hit + 12], [0, 0.8, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const breathe = 1 + Math.max(0, frame - hit) * 0.0007;
  const lineIn = spring({ frame, fps, config: { damping: 16 } });

  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 42%, #3a0d12 0%, #0b0606 58%, #040303 100%)", fontFamily: INTER }}>
      {/* özellik çipleri */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 1 - gather }}>
        <div style={{ color: "#fff", fontWeight: 900, fontSize: spec.hook.title * 0.8, letterSpacing: "-0.03em", marginBottom: 46, opacity: lineIn, transform: `translateY(${(1 - lineIn) * 20}px)` }}>
          {copy.outro.line}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 22, maxWidth: row ? 1500 : 960, transform: `scale(${1 - gather * 0.6})` }}>
          {chips.map((c, i) => {
            const p = spring({ frame: frame - b(i * 0.5), fps, config: { damping: 13, stiffness: 160 } });
            return (
              <div key={c} style={{
                padding: "18px 30px", borderRadius: 999, background: "rgba(255,255,255,.08)", border: "2px solid rgba(255,255,255,.22)",
                color: "#fff", fontWeight: 700, fontSize: spec.label.fontSize * 1.35, opacity: p, transform: `translateY(${(1 - p) * 40}px) scale(${0.8 + 0.2 * p})`,
              }}>
                {c}
              </div>
            );
          })}
        </div>
      </AbsoluteFill>

      {/* logo kilidi */}
      {frame >= hit - 1 && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", transform: `scale(${breathe})` }}>
          <div style={{ display: "flex", flexDirection: spec.logo.direction, alignItems: "center", gap: row ? 40 : 36 }}>
            <NIcon size={spec.logo.icon} style={{ transform: `scale(${lock})` }} glow={0.9} />
            <Wordmark size={spec.logo.word} style={{ opacity: word, transform: `translateY(${(1 - word) * 30}px)` }} />
          </div>
          <div style={{ marginTop: 40, color: "rgba(246,241,231,.9)", fontWeight: 700, fontSize: spec.logo.slogan, letterSpacing: "0.01em", opacity: url, transform: `translateY(${(1 - url) * 20}px)` }}>
            {copy.outro.url}
          </div>
          <div style={{
            marginTop: 34, padding: "20px 46px", borderRadius: 999, background: ACCENT, color: "#fff", fontWeight: 800, fontSize: spec.logo.slogan * 0.95,
            boxShadow: "0 14px 40px rgba(195,30,42,.45)", opacity: cta, transform: `scale(${0.85 + 0.15 * cta})`,
          }}>
            {copy.outro.cta}
          </div>
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{ background: `rgba(255,255,255,${flash})` }} />
      {chips.map((_, i) => <Sfx key={i} at={b(i * 0.5)} name="pop" volume={0.32} />)}
      <Sfx at={hit} name="impact" volume={0.55} />
    </AbsoluteFill>
  );
};
