"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import posthog from "posthog-js";

// Gerçek kullanıcı sinyali (v2.4, tek-operatörlük — roadmap madde 9).
// NEXT_PUBLIC_POSTHOG_KEY boşsa (varsayılan) tamamen no-op — diğer opsiyonel
// entegrasyonlarla (backend'deki Sentry gibi) aynı desen: kod devre dışı
// kalır, hesap açılana kadar hiçbir şey göndermez. PostHog Cloud'un ücretsiz
// katmanı (aylık 1M event) kullanılıyor — VPS'e yeni bir servis EKLEMİYOR.
//
// App Router sayfa geçişleri tam sayfa yenilemesi yapmadığı için pageview'ları
// elle (pathname değişince) gönderiyoruz — `usePathname` kullanılıyor
// (`useSearchParams` DEĞİL, o Suspense gerektirir — search sayfasının mount'ta
// `window.location.search` okuyup Suspense'ten kaçındığı tercihle aynı ruh).
const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY ?? "";
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com";

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const initialized = useRef(false);

  useEffect(() => {
    if (!POSTHOG_KEY || initialized.current) return;
    try {
      posthog.init(POSTHOG_KEY, {
        api_host: POSTHOG_HOST,
        person_profiles: "identified_only", // anonim kullanıcı için profil oluşturma (maliyet)
        capture_pageview: false,            // pageview'ı aşağıda elle gönderiyoruz
        autocapture: true,
      });
      initialized.current = true;
    } catch {
      // Analytics kurulumu ASLA sayfanın çalışmasını engellememeli.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!POSTHOG_KEY || !initialized.current) return;
    posthog.capture("$pageview", { $current_url: window.location.href });
  }, [pathname]);

  return <>{children}</>;
}
