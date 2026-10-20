import type React from "react";
import { type CalculateMetadataFunction, Composition, staticFile } from "remotion";
import type { Lang } from "./copy";
import { FORMATS, type FormatId } from "./formats";
import { Promo, type PromoProps } from "./Promo";
import { DURATION, FPS } from "./timeline";

const LANGS: Lang[] = ["TR", "EN"];
const FMTS: FormatId[] = ["desktop", "mobile"];

const loadManifest: CalculateMetadataFunction<PromoProps> = async ({ props }) => {
  const res = await fetch(staticFile(`captures/${props.lang}-${props.fmt}/manifest.json`));
  if (!res.ok) throw new Error(`manifest bulunamadı (${props.lang}-${props.fmt}) — önce: npm run capture`);
  return { props: { ...props, manifest: await res.json() } };
};

export const Root: React.FC = () => (
  <>
    {LANGS.flatMap((lang) =>
      FMTS.map((fmt) => (
        <Composition
          key={`${lang}-${fmt}`}
          id={`Promo-${lang}-${fmt}`}
          component={Promo}
          durationInFrames={DURATION}
          fps={FPS}
          width={FORMATS[fmt].width}
          height={FORMATS[fmt].height}
          defaultProps={{ lang, fmt }}
          calculateMetadata={loadManifest}
        />
      )),
    )}
  </>
);
