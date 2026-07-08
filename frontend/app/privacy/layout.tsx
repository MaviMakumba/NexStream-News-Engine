import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Gizlilik Politikası",
  description: "NexStream'in topladığı veriler, üçüncü taraf hizmet sağlayıcılar ve kullanıcı hakları.",
};

export default function PrivacyLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
