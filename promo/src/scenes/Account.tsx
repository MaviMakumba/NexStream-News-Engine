// 8. Hesabım: gerçek sayfa yukarıdan aşağı kayar, her bölüm etiketlenir; bülten
// tercihinde yavaşlar: sıklık → konular → anahtar kelime → Kaydet.

import type React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { baseScale, camAt, center, fit, project, union, type CamKey } from "../camera";
import type { AccountLayout, Rect } from "../manifest";
import { localBeat, SCENES } from "../timeline";
import { DAY_BG, usePromo } from "../components/context";
import { Caption, Callout, Caret, Cursor, pathAt, Sfx, typed } from "../components/Overlay";
import { PageLayer, Shot, TypeReveal } from "../components/Page";

export const Account: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { m, view, copy, spec } = usePromo();
  const b = (n: number) => localBeat(SCENES.account.fromBeat, n);
  const steps = m.account.steps;
  const step = (name: string): AccountLayout => (steps.find((s) => s.name === name) ?? steps[0]).layout;
  const L0 = step("account-0");
  const sections = L0.sections.slice(0, 5);
  const col = union(...sections.map((s) => s.rect));
  const narrow = spec.narrow;

  // sabit yakınlaştırma: sütun karenin ~%60'ını kaplasın (mobilde tam genişlik)
  const Z = fit(view, spec.safe, { x: col.x, y: 0, w: col.w, h: 10 }, { margin: narrow ? 0.04 : 0.36, maxZoom: 1.5 }).zoom;
  const visibleH = spec.safe.h / (baseScale(view) * Z);
  const camOn = (r: Rect, f: number): CamKey => {
    const c = fit(view, spec.safe, { x: col.x, y: r.y, w: col.w, h: Math.min(r.h, visibleH * 0.9) }, { margin: 0.02, maxZoom: Z, minZoom: Z });
    return { f, ...c, zoom: Z };
  };

  const nl = step("account-keyword");
  const nlFocus = union(nl.frequency[0], ...Object.values(nl.topics), nl.keyword, nl.save);
  const T = { freq: b(6.4), t1: b(7.4), t2: b(8.1), t3: b(8.8), typeFrom: b(9.3), typeTo: b(10.5), enter: b(10.9), save: b(12) };
  const labelAt = [b(0.2), b(1.4), b(2.6), b(3.8), b(5.6)];
  const cam = camAt(frame, [
    camOn({ ...sections[0].rect, h: Math.min(sections[0].rect.h, visibleH * 0.9) }, 0),
    camOn(sections[1].rect, labelAt[1]),
    camOn(sections[2].rect, labelAt[2]),
    camOn(sections[3].rect, labelAt[3]),
    camOn(nlFocus, labelAt[4]),
    camOn(nlFocus, durationInFrames),
  ]);

  const order: [number, string][] = [[0, "account-0"], [T.freq, "account-freq"], [T.t1, "account-1"], [T.t2, "account-2"], [T.t3, "account-3"], [T.enter, "account-keyword"], [T.save, "account-saved"]];
  const current = order.filter(([f]) => frame >= f).pop()![1];
  const typing = frame >= T.typeFrom && frame < T.enter;
  const tl = step("account-typed");
  const p = typed(frame, T.typeFrom, T.typeTo, tl.keywordText?.chars ?? 1);

  const [l1, l2, l3] = m.account.picks;
  const tgt = (name: string, pick: (l: AccountLayout) => Rect | undefined) => {
    const r = pick(step(name));
    return r ? center(r) : center(nlFocus);
  };
  const keys = [
    { f: T.freq - 14, ...tgt("account-0", (l) => l.frequency[0]), x: tgt("account-0", (l) => l.frequency[0]).x + 200, y: tgt("account-0", (l) => l.frequency[0]).y + 260 },
    { f: T.freq - 2, ...tgt("account-0", (l) => l.frequency[0]) },
    { f: T.t1 - 2, ...tgt("account-freq", (l) => l.topics[l1]) },
    { f: T.t2 - 2, ...tgt("account-1", (l) => l.topics[l2]) },
    { f: T.t3 - 2, ...tgt("account-2", (l) => l.topics[l3]) },
    { f: T.typeFrom - 2, ...tgt("account-3", (l) => l.keyword) },
    { f: T.save - 2, ...tgt("account-keyword", (l) => l.save) },
  ];
  const cur = pathAt(frame, keys);
  const curS = project(view, cam, cur.x, cur.y);
  const curOn = interpolate(frame, [T.freq - 14, T.freq - 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const kt = tl.keywordText;
  const caretS = kt ? project(view, cam, kt.x + kt.w * p + 2, kt.y + kt.h * 0.22) : null;

  return (
    <AbsoluteFill style={{ background: DAY_BG }}>
      <PageLayer cam={cam} bg={DAY_BG}>
        <Shot file={`${typing ? "account-3" : current}.jpg`} />
        {typing && kt && <TypeReveal file="account-typed.jpg" text={kt} p={p} />}
      </PageLayer>
      {sections.map((s, i) => (
        <Callout key={i} rect={s.rect} cam={cam} text={copy.account.sections[i]} from={labelAt[i]} to={i < 4 ? labelAt[i + 1] + 4 : T.freq - 4} side={narrow ? "top" : "right"} pad={4} />
      ))}
      <Callout rect={nlFocus} cam={cam} text={copy.account.newsletter} from={T.t1} to={durationInFrames} side={narrow ? "top" : "right"} pad={10} />
      {typing && caretS && kt && <Caret x={caretS.x} y={caretS.y} h={kt.h * 0.56 * caretS.s} />}
      <Cursor x={curS.x} y={curS.y} clicks={[T.freq, T.t1, T.t2, T.t3, T.typeFrom, T.save]} opacity={curOn} />
      <Caption text={copy.account.caption} from={b(0.3)} to={durationInFrames - 2} />
      {labelAt.map((f, i) => <Sfx key={i} at={f} name="pop" volume={0.32} />)}
      {[T.freq, T.t1, T.t2, T.t3, T.typeFrom, T.save].map((f, i) => <Sfx key={`c${i}`} at={f} name="click" volume={0.6} />)}
      {Array.from({ length: Math.floor((T.typeTo - T.typeFrom) / 3) }, (_, i) => <Sfx key={`k${i}`} at={T.typeFrom + i * 3} name={`key${(i % 3) + 1}`} volume={0.4} />)}
      <Sfx at={T.save + 2} name="ding" volume={0.4} />
    </AbsoluteFill>
  );
};
