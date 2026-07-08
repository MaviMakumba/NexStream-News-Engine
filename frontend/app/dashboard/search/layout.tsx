import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Semantik Arama",
  description: "Anlamsal haber araması — kelime değil, anlam ara.",
  robots: { index: false, follow: false },
};

export default function SearchLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
