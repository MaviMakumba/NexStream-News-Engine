import type { CSSProperties } from "react";

/**
 * Common full-bleed layer style for every canvas effect.
 * Fixed, behind all content, never intercepts pointer events.
 */
export const fxLayerStyle: CSSProperties = {
  position: "fixed",
  inset: 0,
  width: "100%",
  height: "100%",
  zIndex: 0,
  pointerEvents: "none",
};

/** Deterministic-ish jitter helper shared by particle effects. */
export function rand(min: number, max: number): number {
  return min + Math.random() * (max - min);
}
