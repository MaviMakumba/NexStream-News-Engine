"use client";

// Doğrulanmamış kullanıcılar için yumuşak nag banner (v1.15) — Free tier
// erişimini kısıtlamaz, sadece Pro/Kurumsal'a yükseltmeden önce doğrulama
// gerektiğini hatırlatır. DashboardShell + account sayfasında kullanılır.

import { useState } from "react";
import { apiResendVerification } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";

export function EmailVerifyBanner() {
  const { user } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<"sent" | "failed" | null>(null);
  const [dismissed, setDismissed] = useState(false);

  if (!user || user.email_verified || dismissed) return null;

  async function handleResend() {
    setSending(true);
    setNotice(null);
    try {
      await apiResendVerification(lang);
      setNotice("sent");
    } catch {
      setNotice("failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10,
      background: "var(--neu-bg)", border: "1px solid var(--neu)", borderRadius: 12,
      padding: "10px 16px", fontSize: "0.82rem", color: "var(--text2)", marginBottom: 16,
    }}>
      <span>
        ✉ {notice === "sent" ? t.verifyBannerSent : notice === "failed" ? t.verifyBannerFailed : t.verifyBannerText}
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
        {notice !== "sent" && (
          <button onClick={handleResend} disabled={sending} className="btn-secondary"
                  style={{ fontSize: "0.76rem", padding: "6px 12px" }}>
            {sending ? t.loading2 : t.verifyBannerResend}
          </button>
        )}
        <button onClick={() => setDismissed(true)} aria-label="Kapat"
                style={{ background: "none", border: "none", color: "var(--text3)", cursor: "pointer", fontSize: "1rem", lineHeight: 1, padding: 4 }}>
          ×
        </button>
      </div>
    </div>
  );
}
