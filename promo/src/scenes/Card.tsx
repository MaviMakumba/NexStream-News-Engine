// 5. Ana sahne: kahraman haber kartı. Önce tüm rozet/butonlar iki dalgada etiketlenir,
// sonra imleç sırayla İlgili → Kaynaklar → Dinle → Kaydet → Sor'a tıklar; her tıklamanın
// sonucu gerçek arayüz görüntüsünden açılır.

import type React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { camAt, center, fit, identity, project, union } from "../camera";
import type { CardLayout, Rect } from "../manifest";
import { localBeat, SCENES } from "../timeline";
import { ACCENT, DAY_BG, usePromo } from "../components/context";
import { Caption, Callout, Cursor, pathAt, Sfx } from "../components/Overlay";
import { Expand, PageLayer, Shot } from "../components/Page";
import { heroCam } from "./Dive";

/** Kartın içine eklenen panelin (sonraki durumdaki) başlangıcı ve yüksekliği. */
function insertion(prev: CardLayout, next: CardLayout) {
  const panel = next.panels[next.panels.length - 1];
  const h = next.card.h - prev.card.h;
  return { at: panel.y + panel.h - h, h };
}

export const Card: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const ctx = usePromo();
  const { m, view, vh, copy, spec } = ctx;
  const b = (n: number) => localBeat(SCENES.card.fromBeat, n);
  const S = m.card.states;
  const W = view.vw;
  const H = m.feed.clipHeight;

  // tıklama anları (yerel kare)
  const C = { related: b(9), sources: b(12), listen: b(15), save: b(18), ask: b(21) };

  // ── kamera ──
  const start = heroCam(ctx);
  const labelCam = fit(view, spec.safe, S.base.card, { margin: 0.3, maxZoom: 1.35 });
  const relCam = fit(view, spec.safe, S.related.card, { margin: 0.12, maxZoom: 1.35 });
  const srcCam = fit(view, spec.safe, S.sources.card, { margin: 0.1, maxZoom: 1.35 });
  const footCam = fit(view, spec.safe, union(S.listen.footer, S.listen.title), { margin: 0.25, maxZoom: 1.6 });
  const wide = identity(view, vh);
  const askBtn = S.saved.buttons.ask;
  const askCam = fit(view, spec.safe, askBtn, { margin: 0.2, maxZoom: 2.4 });
  const cam = camAt(frame, [
    { f: 0, ...start },
    { f: b(1.5), ...labelCam },
    { f: b(8.5), ...labelCam },
    { f: C.related + 4, ...labelCam },
    { f: C.related + 18, ...relCam },
    { f: C.sources + 4, ...relCam },
    { f: C.sources + 18, ...srcCam },
    { f: C.listen - 4, ...footCam },
    { f: C.save + 2, ...footCam },
    { f: C.save + 12, ...wide },
    { f: C.ask - 8, ...wide },
    { f: C.ask - 2, ...fit(view, spec.safe, union(S.saved.footer, S.saved.title), { margin: 0.2, maxZoom: 1.6 }) },
    { f: durationInFrames, ...askCam, ease: Easing.in(Easing.exp) },
  ]);

  // ── görüntü durumu ──
  const pRel = spring({ frame: frame - C.related - 2, fps, config: { damping: 18 } });
  const pSrc = spring({ frame: frame - C.sources - 2, fps, config: { damping: 18 } });
  const insRel = insertion(S.base, S.related);
  const insSrc = insertion(S.related, S.sources);
  let page: React.ReactNode = <Shot file="feed-after.jpg" />;
  if (frame >= C.related) page = <Expand file="card-related.jpg" at={insRel.at} h={insRel.h} p={pRel} height={H} width={W} />;
  if (frame >= C.sources) page = <Expand file="card-sources.jpg" at={insSrc.at} h={insSrc.h} p={pSrc} height={H} width={W} />;
  if (frame >= C.listen) page = <Shot file="card-listen.jpg" />;
  if (frame >= C.save) page = <Shot file="card-saved.jpg" />;

  // kart dışını hafif karart (odak)
  const focus = S[frame >= C.save ? "saved" : frame >= C.sources ? "sources" : frame >= C.related ? "related" : "base"].card;
  const dimIn = interpolate(frame, [0, b(1.5), C.save, C.save + 10], [0, 1, 1, 0], { extrapolateRight: "clamp" });

  // ── imleç ──
  const btn = (r: Rect) => center(r);
  const offscreen = { x: S.base.card.x + S.base.card.w * 0.85, y: S.base.card.y + S.base.card.h + 260 };
  const userMenu = center(m.card.userMenu);
  const keys = [
    { f: b(7.5), ...offscreen },
    { f: C.related - 3, ...btn(S.base.buttons.related) },
    { f: C.sources - 3, ...btn(S.related.buttons.sources) },
    { f: C.listen - 3, ...btn(S.sources.buttons.listen) },
    { f: C.save - 3, ...btn(S.listen.buttons.save) },
    { f: C.save + 14, ...btn(S.listen.buttons.save) },
    { f: C.ask - 3, ...btn(S.saved.buttons.ask) },
  ];
  const cur = pathAt(frame, keys);
  const curS = project(view, cam, cur.x, cur.y);
  const cursorOn = interpolate(frame, [b(7.5), b(8)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // ── Kaydet: yer imi hesap menüsüne uçar ──
  const fly = interpolate(frame, [C.save + 4, C.save + 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const from = project(view, cam, btn(S.saved.buttons.save).x, btn(S.saved.buttons.save).y);
  const to = project(view, cam, userMenu.x, userMenu.y);
  const flyX = from.x + (to.x - from.x) * fly;
  const flyY = from.y + (to.y - from.y) * fly - Math.sin(fly * Math.PI) * 180;

  // ── Dinle: ses dalgası ──
  const listenOn = frame >= C.listen && frame < C.save + 6;
  // dalga butonun ÜSTÜNDE (yanında Kaydet butonu var)
  const lb = project(view, cam, S.listen.buttons.listen.x + S.listen.buttons.listen.w / 2, S.listen.buttons.listen.y - 6);

  const knowTo = b(8.5);
  // dar kadrajda üst satır rozetleri yan yana sığmaz: etiketler kartın üstünde basamaklanır
  const step = spec.label.fontSize * 1.9 + 12;
  const trustDrop = (S.base.trust.y - S.base.source.y) * project(view, cam, 0, 0).s;
  const gaps = spec.narrow ? { source: 30, topic: 30 + step, trust: 30 + step * 2 + trustDrop } : { source: 30, topic: 86, trust: 30 };
  return (
    <AbsoluteFill style={{ background: DAY_BG }}>
      <PageLayer cam={cam} bg={DAY_BG}>
        {page}
        <div style={{
          position: "absolute", left: -2000, top: -2000, width: W + 4000, height: H + 4000, pointerEvents: "none",
          background: `rgba(20,14,10,${0.32 * dimIn})`,
          clipPath: `polygon(0 0, 100% 0, 100% 100%, 0 100%, 0 ${focus.y + 2000}px, ${focus.x + 2000}px ${focus.y + 2000}px, ${focus.x + 2000}px ${focus.y + focus.h + 2000}px, ${focus.x + focus.w + 2000}px ${focus.y + focus.h + 2000}px, ${focus.x + focus.w + 2000}px ${focus.y + 2000}px, 0 ${focus.y + 2000}px)`,
        }} />
      </PageLayer>

      {/* dalga A: üst satır */}
      <Callout rect={union(S.base.source, S.base.time)} cam={cam} text={copy.card.source} from={b(2)} to={b(5.5)} side="top" gap={gaps.source} />
      <Callout rect={union(S.base.topic, S.base.sentiment)} cam={cam} text={copy.card.topicSentiment} from={b(2.3)} to={b(5.5)} side="top" gap={gaps.topic} />
      <Callout rect={union(S.base.corroboration, S.base.trust)} cam={cam} text={copy.card.trust} from={b(2.6)} to={b(5.5)} side="top" gap={gaps.trust} />
      {/* dalga B: etiketler + butonlar */}
      <Callout rect={S.base.chips} cam={cam} text={copy.card.chips} from={b(5.5)} to={b(8.5)} side="top" />
      <Callout rect={S.base.footer} cam={cam} text={copy.card.actions} from={b(5.8)} to={b(8.5)} side="bottom" />

      {/* tıklama sonuçları */}
      <Callout rect={S.related.panels[0]} cam={cam} text={copy.card.related} from={C.related + 12} to={C.sources - 2} side="bottom" />
      <Callout rect={S.sources.panels[S.sources.panels.length - 1]} cam={cam} text={copy.card.sources} from={C.sources + 12} to={C.listen - 2} side="bottom" />
      <Callout rect={S.listen.buttons.listen} cam={cam} text={copy.card.listen} from={C.listen + 4} to={C.save - 2} side="bottom" />
      <Callout rect={m.card.userMenu} cam={cam} text={copy.card.saved} from={C.save + 20} to={C.ask - 4} side="bottom" />
      <Callout rect={S.saved.buttons.ask} cam={cam} text={copy.card.ask} from={C.ask - 6} to={durationInFrames - 6} side="top" />

      {listenOn && (
        <div style={{ position: "absolute", left: lb.x, top: lb.y - 90, height: 80, display: "flex", alignItems: "flex-end", gap: 7, transform: "translateX(-50%)" }}>
          {Array.from({ length: 9 }, (_, i) => (
            <div key={i} style={{ width: 9, borderRadius: 5, background: ACCENT, height: 10 + Math.abs(Math.sin((frame - C.listen) / 3 + i * 0.9)) * 38 }} />
          ))}
        </div>
      )}
      {fly > 0 && fly < 1 && (
        <div style={{ position: "absolute", left: flyX - 30, top: flyY - 30, fontSize: 60 * (1 - fly * 0.5), filter: "drop-shadow(0 8px 14px rgba(0,0,0,.35))" }}>🔖</div>
      )}

      <Cursor x={curS.x} y={curS.y} clicks={Object.values(C)} opacity={cursorOn} />
      <Caption text={copy.card.captionKnow} from={b(1)} to={knowTo} />
      <Caption text={copy.card.captionDeeper} from={knowTo + 2} to={C.ask} />

      {[b(2), b(2.3), b(2.6), b(5.5), b(5.8)].map((f, i) => <Sfx key={i} at={f} name="pop" volume={0.4} />)}
      {Object.values(C).map((f, i) => <Sfx key={`c${i}`} at={f} name="click" volume={0.7} />)}
      <Sfx at={C.related + 2} name="swoosh" volume={0.3} />
      <Sfx at={C.sources + 2} name="swoosh" volume={0.3} />
      <Sfx at={C.save + 4} name="pop" volume={0.5} />
      <Sfx at={C.save + 21} name="ding" volume={0.35} />
      <Sfx at={durationInFrames - 10} name="whoosh" volume={0.75} />
    </AbsoluteFill>
  );
};
