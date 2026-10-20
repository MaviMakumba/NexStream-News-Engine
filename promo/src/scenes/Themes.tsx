// 3. Tema geçidi: haberler sayfası her vuruşta başka temada. Kareler capture.mjs'in
// Playwright clock ile kare kare aldığı GERÇEK canvas efektleri (Matrix yağmuru vb.).

import type React from "react";
import { AbsoluteFill, Img, interpolate, useCurrentFrame } from "remotion";
import { INTER } from "../fonts";
import { localBeat, SCENES } from "../timeline";
import { capture, usePromo } from "../components/context";
import { Caption, Sfx } from "../components/Overlay";

// Sitenin tema geçişindeki renk flaşı (frontend/lib/theme/registry.ts `flash`).
const FLASH: Record<string, string> = {
  matrix: "#22ff88", godfather: "#c8a24a", cyberpunk: "#ff46c8", dune: "#e0a64e", starwars: "#ffe81f",
  spiderman: "#e62230", batman: "#ffd24a", wolfenstein: "#ff7a2a", night: "#60a5fa", day: "#c31e2a",
};

export const Themes: React.FC = () => {
  const frame = useCurrentFrame();
  const { m, variant, copy, spec } = usePromo();
  const order = m.themes.order;
  const starts = order.map((_, i) => localBeat(SCENES.themes.fromBeat, i));
  const idx = Math.max(0, starts.findLastIndex((s) => frame >= s));
  const theme = order[idx];
  const local = frame - starts[idx];
  const img = Math.min(m.themes.frames - 1, local);
  const punch = interpolate(local, [0, 7], [1.07, 1], { extrapolateRight: "clamp" });
  const flash = interpolate(local, [0, 6], [idx === 0 ? 0.0 : 0.55, 0], { extrapolateRight: "clamp" });
  const enter = idx === 0 ? interpolate(local, [0, 5], [1, 0], { extrapolateRight: "clamp" }) : 0;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${punch})` }}>
        <Img src={capture(variant, `themes/${theme}/${String(img).padStart(2, "0")}.jpg`)} style={{ width: "100%" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: FLASH[theme], opacity: flash, mixBlendMode: "screen" }} />
      <AbsoluteFill style={{ background: "#030a07", opacity: enter }} />
      <div style={{ position: "absolute", ...spec.themeTag, display: "flex", justifyContent: "center" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 14, padding: "10px 22px", borderRadius: 999,
          background: "rgba(10,8,7,.78)", border: `2px solid ${FLASH[theme]}`, color: "#fff",
          fontFamily: INTER, fontWeight: 700, fontSize: spec.label.fontSize * 1.15,
          transform: `scale(${interpolate(local, [0, 5], [1.12, 1], { extrapolateRight: "clamp" })})`,
        }}>
          <span style={{ color: FLASH[theme], fontWeight: 900 }}>{String(idx + 1).padStart(2, "0")}/{order.length}</span>
          <span>{copy.themes.tags[theme]}</span>
        </div>
      </div>
      <Caption text={copy.themes.caption} from={3} to={starts[starts.length - 1] + 10} />
      {starts.slice(1).map((s, i) => <Sfx key={i} at={s} name="flick" volume={0.55} />)}
    </AbsoluteFill>
  );
};
