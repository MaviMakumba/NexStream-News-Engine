// 6. Soru Sor (karttaki "Sor"dan köprü) + 7. semantik arama. İkisi de aynı desen:
// boş hâl → metin tuş tuş yazılır → gönder → sonuç gerçek arayüzden parça parça açılır.

import type React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { camAt, center, fit, project, union } from "../camera";
import { localBeat, SCENES } from "../timeline";
import { DAY_BG, usePromo } from "../components/context";
import { Caption, Callout, Caret, Cursor, pathAt, Sfx, typed } from "../components/Overlay";
import { PageLayer, Shot, TypeReveal } from "../components/Page";

/** Yazma sırasında tuş sesleri (her 3 karede bir, üç farklı tuş). */
const Keys: React.FC<{ from: number; to: number }> = ({ from, to }) => (
  <>
    {Array.from({ length: Math.floor((to - from) / 3) }, (_, i) => (
      <Sfx key={i} at={from + i * 3} name={`key${(i % 3) + 1}`} volume={0.4} />
    ))}
  </>
);

/** Sahneye giriş: hızlı yatay "whip" + bulanıklık. */
function whip(frame: number) {
  const t = interpolate(frame, [0, 9], [1, 0], { extrapolateRight: "clamp" });
  return { transform: `translateX(${t * 18}%)`, filter: `blur(${t * 18}px)`, opacity: 1 - t * 0.4 };
}

export const Ask: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { m, view, copy, spec } = usePromo();
  const b = (n: number) => localBeat(SCENES.ask.fromBeat, n);
  const A = m.ask;
  const ans = A.answer.answer;

  const focus = union(A.answer.user, ans.bubble, A.typed.input);
  const camFull = fit(view, spec.safe, focus, { margin: 0.06, maxZoom: 1.45 });
  // yazarken: sayfa başlığından giriş kutusuna kadar (soru balonu henüz yok)
  const camType = fit(view, spec.safe, union(A.typed.input, { ...A.typed.input, y: A.answer.user.y - (spec.narrow ? 30 : 200), h: 10 }), { margin: 0.06, maxZoom: 1.6 });
  const cam = camAt(frame, [
    { f: 0, ...camType, zoom: camType.zoom * 1.25 },
    { f: b(1), ...camType },
    { f: b(3.8), ...camType },
    { f: b(5), ...camFull },
  ]);

  const T = { from: b(0.6), to: b(3.4), send: b(3.8), answer: b(5.4) };
  const p = typed(frame, T.from, T.to, A.typed.text.chars);
  const lines = Math.max(1, Math.round(ans.text.h / ans.lineHeight));
  const perLine = b(0.6);
  const textDone = T.answer + 6 + lines * perLine;
  const extras = spring({ frame: frame - textDone, fps, config: { damping: 18 } });

  let page: React.ReactNode;
  if (frame < T.send) {
    page = (
      <>
        <Shot file="ask-blank.jpg" top={A.scrolls.blank} />
        <TypeReveal file="ask-typed.jpg" top={A.scrolls.typed} text={A.typed.text} p={p} />
      </>
    );
  } else if (frame < T.answer) {
    page = <Shot file="ask-pending.jpg" top={A.scrolls.pending} />;
  } else {
    const rows = Array.from({ length: lines }, (_, i) => {
      const lp = interpolate(frame, [T.answer + 6 + i * perLine, T.answer + 6 + (i + 1) * perLine], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
      return <Shot key={i} file="ask-answer.jpg" top={A.scrolls.answer} clip={{ x: ans.text.x, y: ans.text.y + i * ans.lineHeight, w: ans.text.w * lp, h: ans.lineHeight + 1 }} />;
    });
    page = (
      <>
        <Shot file="ask-answer-blank.jpg" top={A.scrolls.answerBlank} />
        {rows}
        {[ans.badges, ans.sources, ans.alert].map((r, i) => (
          <Shot key={i} file="ask-answer.jpg" top={A.scrolls.answer} clip={r} opacity={extras} dy={(1 - extras) * 12} />
        ))}
      </>
    );
  }

  const caretS = project(view, cam, A.typed.text.x + A.typed.text.w * p + 2, A.typed.text.y + A.typed.text.h * 0.22);
  const send = center(A.typed.send);
  const cur = pathAt(frame, [
    { f: T.to - 10, x: send.x + 120, y: send.y + 140 },
    { f: T.send - 2, ...send },
    { f: T.send + 30, x: send.x + 60, y: send.y + 200 },
  ]);
  const curS = project(view, cam, cur.x, cur.y);
  const curOn = interpolate(frame, [T.to - 10, T.to - 4, T.send + 18, T.send + 30], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: DAY_BG }}>
      <AbsoluteFill style={whip(frame)}>
        <PageLayer cam={cam} bg={DAY_BG}>{page}</PageLayer>
      </AbsoluteFill>
      {frame >= T.from && frame < T.send && <Caret x={caretS.x} y={caretS.y} h={A.typed.text.h * 0.56 * caretS.s} />}
      <Cursor x={curS.x} y={curS.y} clicks={[T.send]} opacity={curOn} />
      <Callout rect={union(ans.badges, ans.sources)} cam={cam} text={copy.ask.sources} from={textDone + 8} to={durationInFrames} side={spec.narrow ? "top" : "right"} />
      <Callout rect={ans.alert} cam={cam} text={copy.ask.alert} from={textDone + 26} to={durationInFrames} side="bottom" />
      <Caption text={copy.ask.caption} from={b(0.5)} to={durationInFrames - 2} />
      <Keys from={T.from} to={T.to} />
      <Sfx at={T.send} name="click" volume={0.7} />
      <Sfx at={T.send + 1} name="swoosh" volume={0.35} />
      <Sfx at={textDone + 8} name="ding" volume={0.45} />
    </AbsoluteFill>
  );
};

export const Search: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { m, view, copy, spec } = usePromo();
  const b = (n: number) => localBeat(SCENES.search.fromBeat, n);
  const S = m.search;
  const res = S.results;

  const focus = union(S.typed.input, S.typed.button, ...res.results.slice(0, 3));
  const cam = camAt(frame, [
    { f: 0, ...fit(view, spec.safe, union(S.typed.input, S.typed.button), { margin: 0.2, maxZoom: 1.7 }) },
    { f: b(2.6), ...fit(view, spec.safe, union(S.typed.input, S.typed.button), { margin: 0.2, maxZoom: 1.7 }) },
    { f: b(4), ...fit(view, spec.safe, focus, { margin: 0.05, maxZoom: 1.4 }) },
  ]);

  const T = { from: b(0.4), to: b(2.3), go: b(2.7), first: b(3) };
  const p = typed(frame, T.from, T.to, S.typed.text.chars);
  const stagger = b(0.4);
  const scoresAt = T.first + res.results.length * stagger + 6;

  let page: React.ReactNode;
  if (frame < T.go) {
    page = (
      <>
        <Shot file="search-blank.jpg" top={S.scroll} />
        <TypeReveal file="search-typed.jpg" top={S.scroll} text={S.typed.text} p={p} />
      </>
    );
  } else {
    page = (
      <>
        <Shot file="search-results-blank.jpg" top={S.scroll} />
        {res.results.map((r, i) => {
          const rp = spring({ frame: frame - T.first - i * stagger, fps, config: { damping: 16, stiffness: 130 } });
          return <Shot key={i} file="search-results.jpg" top={S.scroll} clip={r} opacity={rp} dy={(1 - rp) * 50} />;
        })}
      </>
    );
  }
  const caretS = project(view, cam, S.typed.text.x + S.typed.text.w * p + 2, S.typed.text.y + S.typed.text.h * 0.22);
  const btnC = center(S.typed.button);
  const cur = pathAt(frame, [
    { f: T.to - 8, x: btnC.x + 60, y: btnC.y + 160 },
    { f: T.go - 2, ...btnC },
    { f: T.go + 30, x: btnC.x + 90, y: btnC.y + 220 },
  ]);
  const curS = project(view, cam, cur.x, cur.y);
  const curOn = interpolate(frame, [T.to - 8, T.to - 2, T.go + 16, T.go + 30], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: DAY_BG }}>
      <AbsoluteFill style={whip(frame)}>
        <PageLayer cam={cam} bg={DAY_BG}>{page}</PageLayer>
      </AbsoluteFill>
      {frame >= T.from && frame < T.go && <Caret x={caretS.x} y={caretS.y} h={S.typed.text.h * 0.56 * caretS.s} />}
      <Cursor x={curS.x} y={curS.y} clicks={[T.go]} opacity={curOn} />
      <Callout rect={union(...res.scores.slice(0, spec.narrow ? 1 : undefined))} cam={cam} text={copy.search.score} from={scoresAt} to={durationInFrames} side={spec.narrow ? "top" : "right"} />
      <Caption text={copy.search.caption} from={b(0.3)} to={durationInFrames - 2} />
      <Keys from={T.from} to={T.to} />
      <Sfx at={T.go} name="click" volume={0.7} />
      {res.results.map((_, i) => <Sfx key={i} at={T.first + i * stagger} name="swoosh" volume={0.22} />)}
      <Sfx at={scoresAt} name="pop" volume={0.45} />
    </AbsoluteFill>
  );
};
