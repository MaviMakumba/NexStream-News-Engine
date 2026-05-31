"use client";

import { createContext, useContext, useState, useEffect } from "react";

export type Theme = "nebula" | "synthwave" | "midnight" | "light";
export type Lang = "TR" | "EN";

interface SettingsCtx {
  theme: Theme;
  lang: Lang;
  setTheme: (t: Theme) => void;
  setLang: (l: Lang) => void;
}

const SettingsContext = createContext<SettingsCtx>({
  theme: "nebula", lang: "TR",
  setTheme: () => {}, setLang: () => {},
});

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("nebula");
  const [lang, setLangState] = useState<Lang>("TR");

  useEffect(() => {
    const t = localStorage.getItem("nxt_theme") as Theme | null;
    const l = localStorage.getItem("nxt_lang") as Lang | null;
    if (t) setThemeState(t);
    if (l) setLangState(l);
  }, []);

  const setTheme = (t: Theme) => { localStorage.setItem("nxt_theme", t); setThemeState(t); };
  const setLang  = (l: Lang)  => { localStorage.setItem("nxt_lang",  l); setLangState(l);  };

  return (
    <SettingsContext.Provider value={{ theme, lang, setTheme, setLang }}>
      <div data-theme={theme} style={{ minHeight: "100vh" }}>
        {children}
      </div>
    </SettingsContext.Provider>
  );
}

export const useSettings = () => useContext(SettingsContext);
