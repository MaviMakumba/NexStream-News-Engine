import type { Metadata } from "next";

export const metadata: Metadata = {
  title: { template: "%s — NexStream", default: "Giriş / Kayıt — NexStream" },
  description: "NexStream hesabınıza giriş yapın veya ücretsiz kaydolun.",
};

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
