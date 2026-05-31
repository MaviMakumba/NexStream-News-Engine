"use client";

import { THEMES } from "./registry";
import type { ThemeId } from "./types";

/**
 * Renders the active theme's cinematic background effect.
 *
 * Keyed by theme id so React remounts the canvas on theme change — this
 * guarantees each effect re-runs its own `setup` with a clean slate instead
 * of inheriting the previous theme's particle state.
 */
export function ThemeBackground({ theme }: { theme: ThemeId }) {
  const Effect = THEMES[theme]?.effect;
  if (!Effect) return null;
  return <Effect key={theme} />;
}
