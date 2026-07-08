import type { Metadata } from "next";

// Token'a bağlı geçiş akışı — dizinlenmesinin bir değeri yok.
export const metadata: Metadata = {
  title: "Şifre Sıfırla",
  robots: { index: false, follow: false },
};

export default function ResetPasswordLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
