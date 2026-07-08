import type { Metadata } from "next";

// Kişiye özel/giriş gerektiren içerik — arama motorlarına indexlenmemeli.
export const metadata: Metadata = {
  title: "Hesabım",
  description: "Plan, kullanım ve API anahtarı yönetimi.",
  robots: { index: false, follow: false },
};

export default function AccountLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
