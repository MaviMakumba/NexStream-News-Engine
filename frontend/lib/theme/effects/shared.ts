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

/**
 * Particle-count multiplier for the active performance profile
 * (`<html data-perf="low">`, set from the settings panel). Effects multiply
 * their column/star/mote counts by this so "low" halves particle density
 * on low-end devices instead of running the full-detail scene.
 */
export function density(): number {
  if (typeof document === "undefined") return 1;
  return document.documentElement.dataset.perf === "low" ? 0.5 : 1;
}
