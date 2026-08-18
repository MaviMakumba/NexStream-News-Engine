"use client";

// Oturum durumu — kimlik artık HttpOnly `nxs_session` cookie'sinde taşınır
// (backend set eder, JS değerini hiç göremez). localStorage sadece kullanıcı
// nesnesinin bir ÖNBELLEĞİ: ilk boyamada "misafir" flaş'ı görülmeden önceki
// oturumu göstermek için. Doğruluk kaynağı her zaman /auth/me — arka planda
// çağrılır, cookie geçersizse oturum otomatik kapatılır.

import { createContext, useContext, useEffect, useLayoutEffect, useState } from "react";
import { fetchMe, apiLogout } from "./api";
import type { User } from "./types";

// SSR'da useLayoutEffect "does nothing on server" uyarısı verir — client'ta
// layout effect (paint ÖNCESİ senkron), server'da normal effect (no-op) kullan.
const useIsomorphicLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;

interface AuthCtx {
  user: User | null;
  isLoading: boolean;
  login: (user: User) => void;
  logout: () => Promise<void>;
  /** Kullanıcı bilgisini backend'den yeniden çeker (tier/rol değişimi sonrası). */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthCtx>({
  user: null, isLoading: true,
  login: () => {}, logout: async () => {},
  refreshUser: async () => {},
});

const USER_KEY = "nxt_user";

function persistUser(user: User) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // SSR ile eşleşmesi için ilk render hep null (guest) — hydration mismatch
  // riski almadan localStorage'daki önbellek hemen aşağıdaki layout effect'te,
  // tarayıcı boyamadan (paint) ÖNCE senkron uygulanır.
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useIsomorphicLayoutEffect(() => {
    try {
      const cached = localStorage.getItem(USER_KEY);
      if (cached) setUser(JSON.parse(cached));
    } catch {}
    setIsLoading(false);

    // Cookie backend'de doğruluk kaynağıdır; önbellek sadece ilk boyama içindir.
    // Cookie yoksa/geçersizse 401 döner → oturumu düşür.
    fetchMe()
      .then((fresh) => { setUser(fresh); persistUser(fresh); })
      .catch(() => {
        localStorage.removeItem(USER_KEY);
        setUser(null);
      });
  }, []);

  // bfcache (back-forward cache) düzeltmesi: tarayıcı geri/ileri tuşuyla bu
  // sayfaya dönerse, sayfa yeniden mount OLMADAN önceki JS durumu dondurulup
  // aynen geri getiriliyor — yani logout() sonrası `user`'ı null yapıp
  // localStorage'ı temizlesek bile, kullanıcı çıkış yapıp başka bir sayfaya
  // gidip GERİ tuşuna basınca bfcache eski (giriş yapılmış) React durumunu
  // aynen gösteriyordu; mount effect'i tekrar çalışmadığı için `/auth/me`
  // hiç yeniden sorulmuyordu (18 Ağu 2026'da kullanıcı bulgusu). Gerçek bir
  // yetki açığı değil — çerez sunucuda zaten geçersiz, herhangi bir API isteği
  // 401 alır — ama kullanıcıya YANLIŞ ŞEKİLDE hâlâ giriş yapılmış gösteriyordu.
  // `pageshow`'un `persisted` bayrağı tam bu durumu (bfcache restore) yakalar.
  useEffect(() => {
    function handlePageShow(event: PageTransitionEvent) {
      if (!event.persisted) return;
      fetchMe()
        .then((fresh) => { setUser(fresh); persistUser(fresh); })
        .catch(() => {
          localStorage.removeItem(USER_KEY);
          setUser(null);
        });
    }
    window.addEventListener("pageshow", handlePageShow);
    return () => window.removeEventListener("pageshow", handlePageShow);
  }, []);

  const login = (user: User) => {
    persistUser(user);
    setUser(user);
  };

  const logout = async () => {
    await apiLogout().catch(() => {});
    localStorage.removeItem(USER_KEY);
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const fresh = await fetchMe();
      setUser(fresh); persistUser(fresh);
    } catch {
      // Tazeleme başarısızsa mevcut kullanıcıyı koru — kritik bir akış değil.
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
