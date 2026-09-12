import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Güvenlik Politikası",
  description: "NexStream'de güvenlik bulgularının nasıl bildirileceği, izinsiz test yasağı ve sorumlu ifşa kuralları.",
};

export default function SecurityLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
