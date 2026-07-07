"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiResetPassword } from "@/lib/api";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

export default function ResetPasswordPage() {
  const router = useRouter();
  const { lang } = useSettings();
  const t = UI[lang];
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setToken(new URLSearchParams(window.location.search).get("token"));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError(t.passwordsDontMatch);
      return;
    }
    if (!token) {
      setError(t.invalidResetLink);
      return;
    }
    setLoading(true);
    try {
      await apiResetPassword(token, password);
      setDone(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.resetPasswordFailed);
    } finally {
      setLoading(false);
    }
  }

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
            {t.resetPasswordTitle}
          </h1>
          <p style={{ fontSize: "0.875rem", color: "var(--text3)" }}>{t.resetPasswordSub}</p>
        </div>

        <div className="card" style={{ padding: 28 }}>
          {done ? (
            <>
              <p style={{ fontSize: "0.9rem", color: "var(--text2)", lineHeight: 1.6, marginBottom: 18 }}>
                {t.resetPasswordSuccess}
              </p>
              <button onClick={() => router.push("/auth/login")} className="btn-primary"
                      style={{ justifyContent: "center", padding: "11px", width: "100%" }}>
                {t.goToLogin}
              </button>
            </>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div>
                <label className="label">{t.newPasswordLabel}</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                       className="input" placeholder="••••••••" required minLength={8}
                       autoComplete="new-password" />
              </div>
              <div>
                <label className="label">{t.confirmPasswordLabel}</label>
                <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
                       className="input" placeholder="••••••••" required minLength={8}
                       autoComplete="new-password" />
              </div>
              {error && (
                <div style={{ background: "var(--neg-bg)", border: "1px solid var(--neg)", borderRadius: 10,
                              padding: "10px 14px", fontSize: "0.84rem", color: "var(--neg)" }}>
                  ⚠ {error}
                </div>
              )}
              <button type="submit" disabled={loading} className="btn-primary" style={{ justifyContent: "center", padding: "11px" }}>
                {loading ? t.loading2 : t.resetPasswordBtn}
              </button>
            </form>
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
