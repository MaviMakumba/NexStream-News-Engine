import { createContext, useContext } from "react";
import { staticFile } from "remotion";
import type { View } from "../camera";
import type { Copy, Lang } from "../copy";
import type { FormatId, FormatSpec } from "../formats";
import type { Manifest } from "../manifest";

export interface PromoCtx {
  lang: Lang;
  copy: Copy;
  fmt: FormatId;
  spec: FormatSpec;
  m: Manifest;
  variant: string;
  view: View;
  vh: number;
}

export const Ctx = createContext<PromoCtx | null>(null);

export function usePromo(): PromoCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("PromoCtx yok");
  return c;
}

/** capture.mjs çıktısındaki bir dosya. */
export const capture = (variant: string, file: string) => staticFile(`captures/${variant}/${file}`);

export const ACCENT = "#c31e2a";
export const ACCENT_LIGHT = "#ff5a64";
export const DAY_BG = "#f5f1e8";
export const INK = "#14110e";
