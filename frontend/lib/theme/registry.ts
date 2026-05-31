import type { ThemeDefinition, ThemeId } from "./types";
import { MatrixRain } from "./effects/MatrixRain";
import { FilmGrain } from "./effects/FilmGrain";
import { NeonRain } from "./effects/NeonRain";
import { SandStorm } from "./effects/SandStorm";
import { Starfield } from "./effects/Starfield";
import { WebStrands } from "./effects/WebStrands";
import { BatSignal } from "./effects/BatSignal";
import { EmberHaze } from "./effects/EmberHaze";

/**
 * The single source of truth for themes.
 *
 * Each entry binds a theme id to its picker metadata + its cinematic
 * background effect. CSS color tokens live in globals.css keyed by the same
 * `data-theme="<id>"`. Adding a theme means: add a ThemeId, an entry here, a
 * CSS block, and (optionally) an effect — no consumer code changes.
 */
export const THEMES: Record<ThemeId, ThemeDefinition> = {
  matrix: {
    id: "matrix",
    labelKey: "matrix",
    tagKey: "matrixTag",
    icon: "ᛃ",
    effect: MatrixRain,
    flash: "#22ff88",
  },
  godfather: {
    id: "godfather",
    labelKey: "godfather",
    tagKey: "godfatherTag",
    icon: "♛",
    effect: FilmGrain,
    flash: "#c8a24a",
  },
  cyberpunk: {
    id: "cyberpunk",
    labelKey: "cyberpunk",
    tagKey: "cyberpunkTag",
    icon: "⌁",
    effect: NeonRain,
    flash: "#ff46c8",
  },
  dune: {
    id: "dune",
    labelKey: "dune",
    tagKey: "duneTag",
    icon: "☼",
    effect: SandStorm,
    flash: "#e0a64e",
  },
  starwars: {
    id: "starwars",
    labelKey: "starwars",
    tagKey: "starwarsTag",
    icon: "✷",
    effect: Starfield,
    flash: "#ffe81f",
  },
  spiderman: {
    id: "spiderman",
    labelKey: "spiderman",
    tagKey: "spidermanTag",
    icon: "✶",
    effect: WebStrands,
    flash: "#e62230",
  },
  batman: {
    id: "batman",
    labelKey: "batman",
    tagKey: "batmanTag",
    icon: "𓂀",
    effect: BatSignal,
    flash: "#ffd24a",
  },
  wolfenstein: {
    id: "wolfenstein",
    labelKey: "wolfenstein",
    tagKey: "wolfensteinTag",
    icon: "⚙",
    effect: EmberHaze,
    flash: "#ff7a2a",
  },
  day: {
    id: "day",
    labelKey: "day",
    tagKey: "dayTag",
    icon: "☀",
    effect: null,
    flash: "#2563eb",
  },
};

/** Ordered list for the picker UI. */
export const THEME_LIST: ThemeDefinition[] = [
  THEMES.matrix,
  THEMES.godfather,
  THEMES.cyberpunk,
  THEMES.dune,
  THEMES.starwars,
  THEMES.spiderman,
  THEMES.batman,
  THEMES.wolfenstein,
  THEMES.day,
];

export const DEFAULT_THEME: ThemeId = "matrix";

export function isThemeId(value: unknown): value is ThemeId {
  return typeof value === "string" && value in THEMES;
}
