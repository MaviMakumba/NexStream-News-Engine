import type { Metadata } from "next";

// Token'a bağlı geçiş akışı — dizinlenmesinin bir değeri yok.
export const metadata: Metadata = {
  title: "E-posta Doğrula",
  robots: { index: false, follow: false },
};

export default function VerifyEmailLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
