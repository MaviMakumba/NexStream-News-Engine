"use client";

import { THEMES } from "./registry";
import type { ThemeId } from "./types";

/**
 * Renders the active theme's cinematic background effect.
 *
 * Keyed by theme id (+ perf profile) so React remounts the canvas on either
 * change — this guarantees each effect re-runs its own `setup` with a clean
 * slate instead of inheriting the previous theme's particle state, and lets
 * a low/high perf toggle actually reduce particle counts immediately instead
 * of waiting for the next resize.
 */
export function ThemeBackground({ theme, perf }: { theme: ThemeId; perf: string }) {
  const Effect = THEMES[theme]?.effect;
  if (!Effect) return null;
  return <Effect key={`${theme}-${perf}`} />;
}
