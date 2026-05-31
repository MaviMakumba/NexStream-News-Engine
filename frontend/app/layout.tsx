import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { SettingsProvider } from "@/lib/settings-context";
import { DEFAULT_THEME } from "@/lib/theme/registry";

export const metadata: Metadata = {
  title: "NexStream — AI Haber Motoru",
  description: "Türkiye ve dünyadan yapay zeka destekli haber analizi",
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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" data-theme={DEFAULT_THEME}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href={FONTS_HREF} />
      </head>
      <body>
        <AuthProvider>
          <SettingsProvider>{children}</SettingsProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
