"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiRegister } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const { user } = await apiRegister(email, password, name);
      login(user);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.registerFailed);
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
            {t.registerTitle}
          </h1>
          <p style={{ fontSize: "0.875rem", color: "var(--text3)" }}>{t.registerSub}</p>
        </div>

        <div className="card" style={{ padding: 28 }}>
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div>
              <label className="label">{t.nameLabel}</label>
              <input value={name} onChange={(e) => setName(e.target.value)}
                     className="input" placeholder={t.namePlaceholder} autoComplete="name" />
            </div>
            <div>
              <label className="label">{t.emailLabel}</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                     className="input" placeholder="siz@ornek.com" required autoComplete="email" />
            </div>
            <div>
              <label className="label">{t.passwordLabel}</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                     className="input" placeholder={t.passwordHint} required minLength={8}
                     autoComplete="new-password" />
            </div>
            {error && (
              <div style={{ background: "var(--neg-bg)", border: "1px solid var(--neg)", borderRadius: 10,
                            padding: "10px 14px", fontSize: "0.84rem", color: "var(--neg)" }}>
                ⚠ {error}
              </div>
            )}
            <button type="submit" disabled={loading} className="btn-primary" style={{ justifyContent: "center", padding: "11px" }}>
              {loading ? t.loading2 : t.registerBtn}
            </button>
          </form>
        </div>

        <p style={{ textAlign: "center", fontSize: "0.76rem", color: "var(--text3)", marginTop: 14, lineHeight: 1.6 }}>
          {t.agreeToTermsPrefix}{" "}
          <Link href="/terms" style={{ color: "var(--text2)", textDecoration: "underline" }}>{t.termsLinkLabel}</Link>
          {" "}{t.agreeToTermsAnd}{" "}
          <Link href="/privacy" style={{ color: "var(--text2)", textDecoration: "underline" }}>{t.privacyLinkLabel}</Link>
          {t.agreeToTermsSuffix}
        </p>

        <p style={{ textAlign: "center", fontSize: "0.84rem", color: "var(--text3)", marginTop: 12 }}>
          {t.haveAccount}{" "}
          <Link href="/auth/login"
                style={{ color: "var(--accent)", textDecoration: "none", fontWeight: 600 }}>
            {t.signIn}
          </Link>
        </p>
      </div>
    </div>
  );
}
