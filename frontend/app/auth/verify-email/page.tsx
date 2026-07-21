"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiVerifyEmail } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

type Status = "pending" | "success" | "error";

export default function VerifyEmailPage() {
  const { refreshUser } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];
  const [status, setStatus] = useState<Status>("pending");
  const [error, setError] = useState("");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setStatus("error");
      setError(t.verifyEmailMissingToken);
      return;
    }
    apiVerifyEmail(token)
      .then(() => {
        setStatus("success");
        refreshUser();
      })
      .catch((err: unknown) => {
        setStatus("error");
        setError(err instanceof Error ? err.message : t.verifyEmailFailed);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      padding: 20, position: "relative",
    }}>
      <div className="grid-bg" style={{
        position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none",
        maskImage: "radial-gradient(ellipse 60% 60% at 50% 50%, black, transparent)",
      }} />
      <div style={{ position: "fixed", top: "20%", right: "30%", width: 400, height: 400, zIndex: 0,
                    background: "radial-gradient(circle, var(--glow2), transparent 70%)", pointerEvents: "none" }} />

      <div style={{ position: "relative", zIndex: 1, width: "100%", maxWidth: 400 }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <Link href="/" style={{ textDecoration: "none", display: "inline-block", marginBottom: 20 }}>
            <span style={{ fontSize: "1.5rem", fontWeight: 900 }}>
              <span style={{ color: "var(--text)" }}>Nex</span>
              <span className="gradient-text">Stream</span>
            </span>
          </Link>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text)", marginBottom: 6 }}>
            {t.verifyEmailTitle}
          </h1>
          <p style={{ fontSize: "0.875rem", color: "var(--text3)" }}>{t.verifyEmailSub}</p>
        </div>

        <div className="card" style={{ padding: 28, textAlign: "center" }}>
          {status === "pending" && (
            <p style={{ fontSize: "0.9rem", color: "var(--text2)" }}>{t.verifyEmailPending}</p>
          )}
          {status === "success" && (
            <>
              <div style={{ fontSize: "2rem", marginBottom: 10 }}>✓</div>
              <p style={{ fontSize: "0.9rem", color: "var(--text2)", lineHeight: 1.6, marginBottom: 18 }}>
                {t.verifyEmailSuccess}
              </p>
              <Link href="/account" className="btn-primary"
                    style={{ justifyContent: "center", padding: "11px", width: "100%", textDecoration: "none" }}>
                {t.goToAccount}
              </Link>
            </>
          )}
          {status === "error" && (
            <>
              <div style={{ background: "var(--neg-bg)", border: "1px solid var(--neg)", borderRadius: 10,
                            padding: "10px 14px", fontSize: "0.84rem", color: "var(--neg)", marginBottom: 18 }}>
                ⚠ {error}
              </div>
              <Link href="/account" className="btn-secondary"
                    style={{ justifyContent: "center", padding: "11px", width: "100%", textDecoration: "none" }}>
                {t.goToAccount}
              </Link>
            </>
          )}
        </div>

        <p style={{ textAlign: "center", fontSize: "0.84rem", color: "var(--text3)", marginTop: 20 }}>
          <Link href="/auth/login"
                style={{ color: "var(--accent)", textDecoration: "none", fontWeight: 600 }}>
            {t.backToLogin}
          </Link>
        </p>
      </div>
    </div>
  );
}
