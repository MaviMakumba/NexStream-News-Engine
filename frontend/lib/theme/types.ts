import type { ComponentType } from "react";

/**
 * Theme identifiers. Adding a new theme = add an id here + a registry entry.
 * Nothing else in the app references theme ids directly (Open/Closed).
 */
export type ThemeId =
  | "matrix"
  | "godfather"
  | "cyberpunk"
  | "dune"
  | "starwars"
  | "spiderman"
  | "batman"
  | "wolfenstein"
  | "day"
  | "night";

/**
 * A cinematic background effect. Each effect is a self-contained client
 * component that paints behind the UI. It receives no props — it reads the
 * active palette from CSS variables so it stays in sync with the tokens.
 */
export type ThemeEffect = ComponentType;

export interface ThemeDefinition {
  id: ThemeId;
  /** i18n key under UI[lang].themes — keeps labels translatable. */
  labelKey: string;
  /** Short glyph shown in the picker. */
  icon: string;
  /** A one-word mood, used for the picker subtitle. */
  tagKey: string;
  /** Animated background. `null` = no canvas (e.g. the clean Day theme). */
  effect: ThemeEffect | null;
  /** Accent color used for the cross-theme transition flash. */
  flash: string;
}
