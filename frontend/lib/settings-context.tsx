"use client";

import { createContext, useContext, useState, useEffect, useLayoutEffect, useRef } from "react";
import { ThemeBackground } from "./theme/ThemeBackground";
import { THEMES, DEFAULT_THEME, isThemeId } from "./theme/registry";
import type { ThemeId } from "./theme/types";

// SSR'da useLayoutEffect "does nothing on server" uyarısı verir — client'ta
// layout effect (paint ÖNCESİ senkron), server'da normal effect (no-op) kullan.
const useIsomorphicLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;

/** Re-exported for back-compat with existing imports. */
export type Theme = ThemeId;
export type Lang = "TR" | "EN";
export type Perf = "low" | "high";

interface SettingsCtx {
  theme: Theme;
  lang: Lang;
  perf: Perf;
  setTheme: (t: Theme) => void;
  setLang: (l: Lang) => void;
  setPerf: (p: Perf) => void;
}

const SettingsContext = createContext<SettingsCtx>({
  theme: DEFAULT_THEME,
  lang: "TR",
  perf: "high",
  setTheme: () => {},
  setLang: () => {},
  setPerf: () => {},
});

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  // SSR ile eşleşmesi için ilk render hep DEFAULT_THEME/TR — hydration mismatch
  // riski almadan gerçek tercih aşağıdaki layout effect'te paint'ten ÖNCE
  // senkron uygulanır (layout.tsx'teki blocking script CSS attribute'unu zaten
  // erkenden düzeltiyor, burası React state'ini/canvas efektini eşitler).
  const [theme, setThemeState] = useState<Theme>(DEFAULT_THEME);
  const [lang, setLangState] = useState<Lang>("TR");
  const [perf, setPerfState] = useState<Perf>("high");
  const [flash, setFlash] = useState<{ color: string; key: number } | null>(null);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useIsomorphicLayoutEffect(() => {
    const stored = localStorage.getItem("nxt_theme");
    const l = localStorage.getItem("nxt_lang") as Lang | null;
    const p = localStorage.getItem("nxt_perf") as Perf | null;
    if (isThemeId(stored)) setThemeState(stored);
    if (l === "TR" || l === "EN") setLangState(l);
    if (p === "low" || p === "high") setPerfState(p);
  }, []);

  // Apply the palette to <html> so :root CSS vars + canvas readers stay in sync.
  useIsomorphicLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  // Canvas effects read data-perf synchronously in their setup() (see
  // lib/theme/effects/shared.ts::density) — this must land before that
  // regular effect runs, which a layout effect guarantees (see ThemeBackground).
  useIsomorphicLayoutEffect(() => {
    document.documentElement.dataset.perf = perf;
  }, [perf]);

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

  const setPerf = (p: Perf) => {
    localStorage.setItem("nxt_perf", p);
    setPerfState(p);
  };

  return (
    <SettingsContext.Provider value={{ theme, lang, perf, setTheme, setLang, setPerf }}>
      <ThemeBackground theme={theme} perf={perf} />
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
