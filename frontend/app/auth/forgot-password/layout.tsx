import type { Metadata } from "next";

// Geçiş amaçlı akış — dizinlenmesinin bir değeri yok.
export const metadata: Metadata = {
  title: "Şifremi Unuttum",
  robots: { index: false, follow: false },
};

export default function ForgotPasswordLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
