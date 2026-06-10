"use client";

// Oturum durumu (token + kullanıcı) — localStorage'da saklanır.
// Sayfa açılışında /auth/me ile tazelenir: tier veya is_admin backend'de
// değiştiyse (örn. dev-mode yükseltme, admin atama) UI güncel kalır;
// token geçersizse oturum otomatik kapatılır.

import { createContext, useContext, useEffect, useState } from "react";
import { fetchMe } from "./api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  /** Kullanıcı bilgisini backend'den yeniden çeker (tier/is_admin değişimi sonrası). */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthCtx>({
  user: null, token: null, isLoading: true,
  login: () => {}, logout: () => {},
  refreshUser: async () => {},
});

const TOKEN_KEY = "nxt_token";
const USER_KEY = "nxt_user";

function persistUser(user: User) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(TOKEN_KEY);
      const u = localStorage.getItem(USER_KEY);
      if (stored && u) { setToken(stored); setUser(JSON.parse(u)); }
    } catch {}
    setIsLoading(false);

    // Arka planda taze veriyi çek; 401 ise oturum düşmüştür → temizle.
    if (stored) {
      fetchMe(stored)
        .then((fresh) => { setUser(fresh); persistUser(fresh); })
        .catch(() => {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
          setToken(null); setUser(null);
        });
    }
  }, []);

  const login = (token: string, user: User) => {
    localStorage.setItem(TOKEN_KEY, token);
    persistUser(user);
    setToken(token); setUser(user);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null); setUser(null);
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const fresh = await fetchMe(token);
      setUser(fresh); persistUser(fresh);
    } catch {
      // Tazeleme başarısızsa mevcut kullanıcıyı koru — kritik bir akış değil.
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
