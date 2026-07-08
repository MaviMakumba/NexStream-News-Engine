"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Navbar } from "@/components/Navbar";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Wait for /auth/me resolution before redirecting
    if (!isLoading && !user) router.replace("/auth/login");
  }, [isLoading, user]); // intentionally omit router — stable reference

  if (isLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <div className="gradient-text" style={{ fontSize: "1.4rem", fontWeight: 800 }}>NexStream</div>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)",
                        animation: "glow-pulse 1.5s ease-in-out infinite" }} />
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div style={{ minHeight: "100vh" }}>
      <Navbar />
      <main style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 20px" }}>
        {children}
      </main>
    </div>
  );
}
