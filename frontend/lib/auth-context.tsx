"use client";

import { createContext, useContext, useEffect, useState } from "react";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx>({
  user: null, token: null, isLoading: true,
  login: () => {}, logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const t = localStorage.getItem("nxt_token");
      const u = localStorage.getItem("nxt_user");
      if (t && u) { setToken(t); setUser(JSON.parse(u)); }
    } catch {}
    setIsLoading(false);
  }, []);

  const login = (token: string, user: User) => {
    localStorage.setItem("nxt_token", token);
    localStorage.setItem("nxt_user", JSON.stringify(user));
    setToken(token); setUser(user);
  };

  const logout = () => {
    localStorage.removeItem("nxt_token");
    localStorage.removeItem("nxt_user");
    setToken(null); setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
