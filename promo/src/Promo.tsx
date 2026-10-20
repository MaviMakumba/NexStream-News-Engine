import type React from "react";
import { AbsoluteFill, Html5Audio, interpolate, Sequence, staticFile, useVideoConfig } from "remotion";
import { COPY, type Lang } from "./copy";
import { FORMATS, type FormatId } from "./formats";
import type { Manifest } from "./manifest";
import { MUSIC, sceneRange, type SceneName } from "./timeline";
import { Ctx } from "./components/context";
import { Hook, LogoReveal } from "./scenes/Intro";
import { Themes } from "./scenes/Themes";
import { Dive } from "./scenes/Dive";
import { Card } from "./scenes/Card";
import { Ask, Search } from "./scenes/AskSearch";
import { Account } from "./scenes/Account";
import { Mail } from "./scenes/Mail";
import { Outro } from "./scenes/Outro";

export interface PromoProps {
  lang: Lang;
  fmt: FormatId;
  manifest?: Manifest;
  [key: string]: unknown;
}

const SCENE_LIST: [SceneName, React.FC][] = [
  ["hook", Hook], ["logo", LogoReveal], ["themes", Themes], ["dive", Dive], ["card", Card],
  ["ask", Ask], ["search", Search], ["account", Account], ["mail", Mail], ["outro", Outro],
];

const MUSIC_VOL = 0.8;

const Music: React.FC = () => {
  const { fps } = useVideoConfig();
  const { partA: A, partB: B, crossfadeFrames: X } = MUSIC;
  const durA = A.videoTo - A.videoFrom + X;
  return (
    <>
      <Sequence from={A.videoFrom} durationInFrames={durA} name="müzik A">
        <Html5Audio
          src={staticFile(MUSIC.src)}
          trimBefore={Math.round(A.trackFromSec * fps)}
          volume={(f) => interpolate(f, [0, 100, 120, durA - X, durA], [0.35, 0.55, MUSIC_VOL, MUSIC_VOL, 0], { extrapolateRight: "clamp" })}
        />
      </Sequence>
      <Sequence from={B.videoFrom} name="müzik B (son cümle)">
        <Html5Audio
          src={staticFile(MUSIC.src)}
          trimBefore={Math.round(B.trackFromSec * fps)}
          volume={(f) => interpolate(f, [0, X], [0, MUSIC_VOL], { extrapolateRight: "clamp" })}
        />
      </Sequence>
    </>
  );
};

export const Promo: React.FC<PromoProps> = ({ lang, fmt, manifest }) => {
  if (!manifest) throw new Error(`manifest yok: önce 'npm run capture -- ${lang} ${fmt}'`);
  const spec = FORMATS[fmt];
  const value = {
    lang, copy: COPY[lang], fmt, spec, m: manifest, variant: `${lang}-${fmt}`,
    view: { W: spec.width, H: spec.height, vw: manifest.viewport.width }, vh: manifest.viewport.height,
  };
  return (
    <Ctx.Provider value={value}>
      <AbsoluteFill style={{ background: "#000" }}>
        {SCENE_LIST.map(([name, Scene]) => {
          const r = sceneRange(name);
          return (
            <Sequence key={name} name={name} from={r.from} durationInFrames={r.duration}>
              <Scene />
            </Sequence>
          );
        })}
        <Music />
      </AbsoluteFill>
    </Ctx.Provider>
  );
};
