// Sayfa koordinatından (CSS px) kareye (video px) dönüşüm. Kamera: karenin ortasına
// gelen sayfa noktası (cx, cy) + yakınlaştırma. zoom=1 → sayfanın görünüm genişliği
// karenin genişliğini tam doldurur.

import { Easing, interpolate } from "remotion";
import type { Rect } from "./manifest";

export interface Cam { cx: number; cy: number; zoom: number }
export interface CamKey extends Cam { f: number; ease?: (t: number) => number }

export interface View { W: number; H: number; vw: number }

export const baseScale = (v: View) => v.W / v.vw;

export function project(v: View, cam: Cam, x: number, y: number) {
  const s = baseScale(v) * cam.zoom;
  return { x: v.W / 2 + (x - cam.cx) * s, y: v.H / 2 + (y - cam.cy) * s, s };
}

export function projectRect(v: View, cam: Cam, r: Rect): Rect {
  const p = project(v, cam, r.x, r.y);
  return { x: p.x, y: p.y, w: r.w * p.s, h: r.h * p.s };
}

/** Bir dikdörtgeni güvenli alanın ortasına, `margin` (0-1) boşlukla oturtan kamera. */
export function fit(v: View, safe: Rect, r: Rect, opts: { margin?: number; maxZoom?: number; minZoom?: number } = {}): Cam {
  const margin = opts.margin ?? 0.12;
  const s0 = baseScale(v);
  const zoom = Math.min(
    opts.maxZoom ?? 1.6,
    Math.max(opts.minZoom ?? 1, Math.min((safe.w * (1 - margin)) / (r.w * s0), (safe.h * (1 - margin)) / (r.h * s0))),
  );
  const s = s0 * zoom;
  // güvenli alanın merkezi karenin merkezinden kaydırılmış olabilir
  const safeCx = safe.x + safe.w / 2;
  const safeCy = safe.y + safe.h / 2;
  return { cx: r.x + r.w / 2 - (safeCx - v.W / 2) / s, cy: r.y + r.h / 2 - (safeCy - v.H / 2) / s, zoom };
}

/** Görünüm (viewport) ekran görüntüsünü birebir gösteren kamera. */
export const identity = (v: View, vh: number, scroll = 0): Cam => ({ cx: v.vw / 2, cy: scroll + vh / 2, zoom: 1 });

const defaultEase = Easing.inOut(Easing.cubic);

export function camAt(frame: number, keys: CamKey[]): Cam {
  if (frame <= keys[0].f) return keys[0];
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1];
    const b = keys[i];
    if (frame <= b.f) {
      const t = interpolate(frame, [a.f, b.f], [0, 1], { easing: b.ease ?? defaultEase });
      // yakınlaştırma logaritmik ölçekte enterpolasyon → hız hissi sabit
      const zoom = Math.exp(Math.log(a.zoom) + (Math.log(b.zoom) - Math.log(a.zoom)) * t);
      return { cx: a.cx + (b.cx - a.cx) * t, cy: a.cy + (b.cy - a.cy) * t, zoom };
    }
  }
  return keys[keys.length - 1];
}

export const union = (...rs: (Rect | null | undefined)[]): Rect => {
  const v = rs.filter(Boolean) as Rect[];
  const x = Math.min(...v.map((r) => r.x));
  const y = Math.min(...v.map((r) => r.y));
  return { x, y, w: Math.max(...v.map((r) => r.x + r.w)) - x, h: Math.max(...v.map((r) => r.y + r.h)) - y };
};

export const center = (r: Rect) => ({ x: r.x + r.w / 2, y: r.y + r.h / 2 });
