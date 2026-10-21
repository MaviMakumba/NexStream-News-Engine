// Gerçek arayüz görüntülerini sayfa koordinatında yerleştiren katman. İçindeki her şey
// CSS pikseliyle konumlanır, kamera dönüşümü katmanın tamamına uygulanır.

import type React from "react";
import { AbsoluteFill, Img } from "remotion";
import { baseScale, type Cam } from "../camera";
import type { Rect, TextBox } from "../manifest";
import { capture, usePromo } from "./context";

export const PageLayer: React.FC<{ cam: Cam; bg?: string; style?: React.CSSProperties; children: React.ReactNode }> = ({ cam, bg, style, children }) => {
  const { view } = usePromo();
  const s = baseScale(view) * cam.zoom;
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: bg, ...style }}>
      <div style={{
        position: "absolute", left: 0, top: 0, width: view.vw,
        transformOrigin: "0 0", transform: `translate(${view.W / 2 - cam.cx * s}px, ${view.H / 2 - cam.cy * s}px) scale(${s})`,
      }}>
        {children}
      </div>
    </AbsoluteFill>
  );
};

/**
 * Bir ekran görüntüsü. `top`: görüntünün sayfadaki üst kenarı (görünüm görüntülerinde
 * kaydırma miktarı). `clip` verilirse yalnız o bölge çizilir; `dy` bölgeyi dikeyde kaydırır.
 */
export const Shot: React.FC<{ file: string; top?: number; clip?: Rect; dy?: number; opacity?: number; style?: React.CSSProperties }> = ({ file, top = 0, clip, dy = 0, opacity = 1, style }) => {
  const { variant, view } = usePromo();
  const img = <Img src={capture(variant, file)} style={{ position: "absolute", left: clip ? -clip.x : 0, top: clip ? top - clip.y : top, width: view.vw, maxWidth: "none" }} />;
  if (!clip) return <div style={{ position: "absolute", inset: 0, opacity, ...style }}>{img}</div>;
  return (
    <div style={{ position: "absolute", left: clip.x, top: clip.y + dy, width: clip.w, height: Math.max(0, clip.h), overflow: "hidden", opacity, ...style }}>
      {img}
    </div>
  );
};

/** Yazma animasyonu: `file` (metin yazılmış hâl) yalnız metnin ilk p kadarı görünecek şekilde kırpılır. */
export const TypeReveal: React.FC<{ file: string; top?: number; text: TextBox; p: number }> = ({ file, top = 0, text, p }) => (
  <Shot file={file} top={top} clip={{ x: text.x - 2, y: text.y, w: text.w * p + 2, h: text.h }} />
);

/**
 * Genişleyen içerik: `file` (sonraki durum) görüntüsünde [at, at+h) bölgesi yeni eklenen
 * panel. p=0 → önceki durumla aynı görünür, p=1 → sonraki durum.
 */
export const Expand: React.FC<{ file: string; at: number; h: number; p: number; height: number; width: number; top?: number }> = ({ file, at, h, p, height, width, top = 0 }) => (
  <>
    <Shot file={file} top={top} clip={{ x: 0, y: top, w: width, h: at - top }} />
    <Shot file={file} top={top} clip={{ x: 0, y: at, w: width, h: h * p }} />
    <Shot file={file} top={top} clip={{ x: 0, y: at + h, w: width, h: top + height - (at + h) }} dy={-h * (1 - p)} />
  </>
);
