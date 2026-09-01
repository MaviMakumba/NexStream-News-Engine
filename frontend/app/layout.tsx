import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { SavedArticlesProvider } from "@/lib/saved-context";
import { SettingsProvider } from "@/lib/settings-context";
import { DEFAULT_THEME } from "@/lib/theme/registry";
import { ServiceWorkerRegistration } from "@/components/ServiceWorkerRegistration";
import { AnalyticsProvider } from "@/components/AnalyticsProvider";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://nexstream.news";
const SITE_TITLE = "NexStream — AI Haber Motoru";
const SITE_DESCRIPTION = "Türkiye ve dünyadan yapay zeka destekli haber analizi: duygu analizi, semantik arama ve ilişki grafı tek platformda.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { template: "%s — NexStream", default: SITE_TITLE },
  description: SITE_DESCRIPTION,
  openGraph: {
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    url: SITE_URL,
    siteName: "NexStream",
    locale: "tr_TR",
    type: "website",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: SITE_TITLE }],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    images: ["/og-image.png"],
  },
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "NexStream",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#f3f1ec",
};

// One combined Google Fonts request covering every theme's display face.
const FONTS_HREF =
  "https://fonts.googleapis.com/css2?" +
  [
    "family=Inter:wght@400;500;600;700;800;900",
    "family=Share+Tech+Mono",
    "family=Playfair+Display:wght@600;700;800;900",
    "family=Cinzel:wght@600;700;800",
    "family=Orbitron:wght@500;700;900",
    "family=Russo+One",
    "family=Bangers",
    "family=Oswald:wght@400;500;600;700",
    "family=Black+Ops+One",
  ].join("&") +
  "&display=swap";

// İlk boyamadan (paint) ÖNCE çalışır — localStorage'daki temayı senkron uygular,
// böylece sayfa her açılışta varsayılan (day) temayla yanıp kullanıcının
// gerçek temasına geçmez. React state'i settings-context.tsx'te aynı değeri
// lazy initializer ile okur, ikisi arasında fark olmaz.
const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem('nxt_theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // middleware.ts'in request header'ına yazdığı nonce — CSP'nin script-src'sinde
  // aynı değer var, bu script'e basılmazsa nonce'lu policy tarafından bloklanır.
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <html lang="tr" data-theme={DEFAULT_THEME} suppressHydrationWarning>
      <head>
        <script nonce={nonce} dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href={FONTS_HREF} />
      </head>
      <body>
        <ServiceWorkerRegistration />
        <AnalyticsProvider>
          <AuthProvider>
            <SavedArticlesProvider>
              <SettingsProvider>{children}</SettingsProvider>
            </SavedArticlesProvider>
          </AuthProvider>
        </AnalyticsProvider>
      </body>
    </html>
  );
}
