"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Navbar } from "@/components/Navbar";
import { LiveTicker } from "@/components/LiveTicker";
import { AuthLoadingScreen } from "@/components/AuthLoadingScreen";
import { EmailVerifyBanner } from "@/components/EmailVerifyBanner";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Wait for /auth/me resolution before redirecting
    if (!isLoading && !user) router.replace("/auth/login");
  }, [isLoading, user]); // intentionally omit router — stable reference

  if (isLoading) return <AuthLoadingScreen />;
  if (!user) return null;

  return (
    <div style={{ minHeight: "100vh" }}>
      <Navbar />
      <LiveTicker />
      <main style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 20px" }}>
        <EmailVerifyBanner />
        {children}
      </main>
    </div>
  );
}
