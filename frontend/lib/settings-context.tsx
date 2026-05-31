"use client";

import { createContext, useContext, useState, useEffect, useRef } from "react";
import { ThemeBackground } from "./theme/ThemeBackground";
import { THEMES, DEFAULT_THEME, isThemeId } from "./theme/registry";
import type { ThemeId } from "./theme/types";

/** Re-exported for back-compat with existing imports. */
export type Theme = ThemeId;
export type Lang = "TR" | "EN";

interface SettingsCtx {
  theme: Theme;
  lang: Lang;
  setTheme: (t: Theme) => void;
  setLang: (l: Lang) => void;
}

const SettingsContext = createContext<SettingsCtx>({
  theme: DEFAULT_THEME,
  lang: "TR",
  setTheme: () => {},
  setLang: () => {},
});

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(DEFAULT_THEME);
  const [lang, setLangState] = useState<Lang>("TR");
  const [flash, setFlash] = useState<{ color: string; key: number } | null>(null);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Hydrate persisted prefs.
  useEffect(() => {
    const stored = localStorage.getItem("nxt_theme");
    const l = localStorage.getItem("nxt_lang") as Lang | null;
    if (isThemeId(stored)) setThemeState(stored);
    if (l === "TR" || l === "EN") setLangState(l);
  }, []);

  // Apply the palette to <html> so :root CSS vars + canvas readers stay in sync.
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const setTheme = (t: Theme) => {
    if (t === theme) return;
    localStorage.setItem("nxt_theme", t);
    setThemeState(t);
    // Cinematic cross-fade flash in the incoming theme's signature color.
    setFlash({ color: THEMES[t].flash, key: Date.now() });
    if (flashTimer.current) clearTimeout(flashTimer.current);
    flashTimer.current = setTimeout(() => setFlash(null), 700);
  };

  const setLang = (l: Lang) => {
    localStorage.setItem("nxt_lang", l);
    setLangState(l);
  };

  return (
    <SettingsContext.Provider value={{ theme, lang, setTheme, setLang }}>
      <ThemeBackground theme={theme} />
      <div className="app-shell">{children}</div>
      {flash && (
        <div
          key={flash.key}
          className="theme-flash"
          style={{ "--flash": flash.color } as React.CSSProperties}
          aria-hidden
        />
      )}
    </SettingsContext.Provider>
  );
}

export const useSettings = () => useContext(SettingsContext);
