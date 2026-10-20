// 4. Akışa dalış: sayfa 3B eğilip oturur, "CANLI" şeritten yeni haber düşer, piyasa
// şeridi / gündem / filtreler etiketlenir, kamera kahraman karta yönelir (5. sahneye köprü).

import type React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { camAt, fit, identity, union } from "../camera";
import { localBeat, SCENES } from "../timeline";
import { DAY_BG, usePromo } from "../components/context";
import { Caption, Callout, Sfx } from "../components/Overlay";
import { Expand, PageLayer, Shot } from "../components/Page";

export function heroCam(ctx: ReturnType<typeof usePromo>) {
  const { m, view, spec } = ctx;
  return fit(view, spec.safe, m.card.states.base.card, { margin: 0.08, maxZoom: 1.5 });
}

export const Dive: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const ctx = usePromo();
  const { m, view, vh, copy, spec } = ctx;
  const b = (n: number) => localBeat(SCENES.dive.fromBeat, n);
  const { before, after } = m.feed;

  // dar kadrajda (mobil) tüm üst bölge sığmaz → piyasa şeridinden filtrelere kadar
  const top = spec.narrow
    ? union(after.market, after.live, after.trending, after.filters)
    : union(after.nav, after.market, after.live, after.trending, after.filters, after.cards[0]);
  const id = identity(view, vh);
  const topCam = fit(view, spec.safe, top, { margin: 0.04, maxZoom: 1.25 });
  const cam = camAt(frame, [
    { f: 0, ...id },
    { f: b(1.5), ...topCam },
    { f: b(9.5), ...topCam },
    { f: durationInFrames, ...heroCam(ctx) },
  ]);

  // 3B dalış: sayfa geriye yatıp yerine oturur
  const tilt = spring({ frame, fps, config: { damping: 15, stiffness: 90 } });
  const rot = interpolate(tilt, [0, 1], [24, 0]);
  const lift = interpolate(tilt, [0, 1], [0.86, 1]);

  const drop = b(3);
  const p = frame < drop ? 0 : spring({ frame: frame - drop, fps, config: { damping: 16, stiffness: 120 } });
  const insertAt = after.cards[0].y - 0;
  const insertH = after.cards[1].y - after.cards[0].y;

  return (
    <AbsoluteFill style={{ background: "#0d0b09", perspective: 1800 }}>
      <AbsoluteFill style={{ transform: `rotateX(${rot}deg) scale(${lift})`, transformOrigin: "50% 100%" }}>
        <PageLayer cam={cam} bg={DAY_BG}>
          {frame < drop ? (
            <Shot file="feed-before.jpg" />
          ) : (
            <Expand file="feed-after.jpg" at={insertAt} h={insertH} p={p} height={m.feed.clipHeight} width={view.vw} />
          )}
        </PageLayer>
      </AbsoluteFill>
      <Callout rect={before.live} cam={cam} text={copy.dive.live} from={b(1.8)} to={b(6)} side="bottom" />
      <Callout rect={after.market} cam={cam} text={copy.dive.market} from={b(5.5)} to={b(10)} side="bottom" gap={70} />
      <Callout rect={after.trending} cam={cam} text={copy.dive.trending} from={b(6.5)} to={b(10)} side={spec.narrow ? "top" : "right"} />
      <Callout rect={after.filters} cam={cam} text={copy.dive.filters} from={b(7.5)} to={b(10)} side={spec.narrow ? "bottom" : "right"} />
      <Caption text={copy.dive.caption} from={b(1)} to={durationInFrames - 4} />
      <Sfx at={0} name="whoosh" volume={0.7} />
      <Sfx at={drop} name="pop" volume={0.6} />
      <Sfx at={b(5.5)} name="pop" volume={0.35} />
      <Sfx at={b(6.5)} name="pop" volume={0.35} />
      <Sfx at={b(7.5)} name="pop" volume={0.35} />
    </AbsoluteFill>
  );
};
