import type { Metadata } from "next";
import { DashboardShell } from "./DashboardShell";

// Kişiye özel/giriş gerektiren içerik — arama motorlarına indexlenmemeli.
export const metadata: Metadata = {
  title: "Haberler",
  description: "Yapay zeka destekli, kişiselleştirilmiş haber akışı.",
  robots: { index: false, follow: false },
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <DashboardShell>{children}</DashboardShell>;
}
