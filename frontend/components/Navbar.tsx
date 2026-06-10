"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { apiLogout } from "@/lib/api";
import { TierBadge } from "./TierBadge";
import { UI } from "@/lib/i18n";
import { THEME_LIST } from "@/lib/theme/registry";

export function Navbar() {
  const { user, token, logout } = useAuth();
  const { theme, lang, setTheme, setLang } = useSettings();
  const router = useRouter();
  const pathname = usePathname();
  const [userMenu, setUserMenu] = useState(false);
  const [settings, setSettings] = useState(false);
  const t = UI[lang];

  const close = () => { setUserMenu(false); setSettings(false); };

  async function handleLogout() {
    if (token) await apiLogout(token).catch(() => {});
    logout();
    close();
    router.push("/");
  }

  // Yönetim linki sadece admin rolündeki kullanıcıya görünür (v1.11).
  const navLinks = [
    { href: "/dashboard",        label: t.dashboard },
    { href: "/dashboard/search", label: t.search },
    ...(user?.is_admin ? [{ href: "/admin/usage", label: t.admin }] : []),
  ];

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");

  return (
    <>
      {(userMenu || settings) && (
        <div style={{ position: "fixed", inset: 0, zIndex: 30 }} onClick={close} />
      )}

      <nav style={{
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        position: "sticky", top: 0, zIndex: 40,
      }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 20px",
                      display: "flex", alignItems: "center", height: 56, gap: 8 }}>

          {/* Logo */}
          <Link href="/" style={{ textDecoration: "none", marginRight: 8, flexShrink: 0 }}>
            <span className="font-display" style={{ fontSize: "1.15rem", fontWeight: 800 }}>
              <span style={{ color: "var(--text)" }}>Nex</span>
              <span className="gradient-text">Stream</span>
            </span>
          </Link>

          {/* Nav links */}
          <div style={{ display: "flex", alignItems: "center", gap: 2, flex: 1 }}>
            {navLinks.map((l) => (
              <Link key={l.href} href={l.href} style={{
                padding: "5px 12px", borderRadius: 8, fontSize: "0.82rem", fontWeight: 500,
                textDecoration: "none", transition: "all 0.15s",
                color: isActive(l.href) ? "var(--accent)" : "var(--text2)",
                background: isActive(l.href) ? "var(--accent-soft)" : "transparent",
                border: isActive(l.href) ? "1px solid var(--accent-line)" : "1px solid transparent",
              }}>
                {l.label}
              </Link>
            ))}
          </div>

          {/* Right side */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>

            {/* Settings */}
            <div style={{ position: "relative" }}>
              <button onClick={() => { setSettings(!settings); setUserMenu(false); }}
                      title={t.settings}
                      style={{
                        background: settings ? "var(--accent-soft)" : "none",
                        border: `1px solid ${settings ? "var(--border2)" : "var(--border)"}`,
                        borderRadius: 8, color: settings ? "var(--accent)" : "var(--text3)",
                        cursor: "pointer", padding: "5px 10px", fontSize: "0.9rem",
                        transition: "all 0.15s", lineHeight: 1,
                      }}>
                ⚙
              </button>

              {settings && (
                <div className="glass" style={{
                  position: "absolute", right: 0, top: "calc(100% + 8px)", width: 268,
                  borderRadius: 14, padding: 16, boxShadow: "0 16px 48px rgba(0,0,0,.55)", zIndex: 50,
                }}>
                  <div className="section-label" style={{ marginBottom: 10 }}>{t.theme}</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4,
                                maxHeight: 320, overflowY: "auto", marginBottom: 16 }}>
                    {THEME_LIST.map((th) => {
                      const active = theme === th.id;
                      return (
                        <button key={th.id} onClick={() => setTheme(th.id)}
                                style={{
                                  display: "flex", alignItems: "center", gap: 10,
                                  padding: "8px 10px", borderRadius: 10, cursor: "pointer",
                                  textAlign: "left", transition: "all 0.15s",
                                  border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
                                  background: active ? "var(--accent-soft)" : "rgba(0,0,0,.2)",
                                }}>
                          <span style={{
                            width: 26, height: 26, borderRadius: 8, flexShrink: 0,
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: "0.95rem", color: active ? "var(--accent)" : "var(--text2)",
                            background: active ? "var(--surface)" : "transparent",
                            border: `1px solid ${active ? "var(--accent-line)" : "var(--border)"}`,
                          }}>
                            {th.icon}
                          </span>
                          <span style={{ display: "flex", flexDirection: "column", lineHeight: 1.25 }}>
                            <span style={{ fontSize: "0.84rem", fontWeight: 700,
                                           color: active ? "var(--accent)" : "var(--text)" }}>
                              {t[th.labelKey]}
                            </span>
                            <span style={{ fontSize: "0.7rem", color: "var(--text3)" }}>
                              {t[th.tagKey]}
                            </span>
                          </span>
                        </button>
                      );
                    })}
                  </div>

                  <div className="section-label" style={{ marginBottom: 10 }}>{t.language}</div>
                  <div style={{ display: "flex", gap: 6 }}>
                    {(["TR", "EN"] as const).map((l) => (
                      <button key={l} onClick={() => setLang(l)}
                              style={{
                                flex: 1, padding: "6px", borderRadius: 8, fontSize: "0.82rem",
                                cursor: "pointer", fontWeight: 600, transition: "all 0.15s",
                                border: `1px solid ${lang === l ? "var(--accent)" : "var(--border)"}`,
                                background: lang === l ? "var(--accent-soft)" : "rgba(0,0,0,.2)",
                                color: lang === l ? "var(--accent)" : "var(--text2)",
                              }}>
                        {l === "TR" ? "🇹🇷 TR" : "🇬🇧 EN"}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Auth */}
            {user ? (
              <div style={{ position: "relative" }}>
                <button onClick={() => { setUserMenu(!userMenu); setSettings(false); }}
                        style={{
                          display: "flex", alignItems: "center", gap: 8,
                          padding: "5px 12px", borderRadius: 8,
                          background: userMenu ? "var(--accent-soft)" : "var(--surface)",
                          border: `1px solid ${userMenu ? "var(--border2)" : "var(--border)"}`,
                          color: "var(--text)", cursor: "pointer", fontSize: "0.82rem",
                          transition: "all 0.15s", maxWidth: 240,
                        }}>
                  <div style={{ width: 22, height: 22, borderRadius: "50%", flexShrink: 0,
                                background: "linear-gradient(135deg, var(--accent), var(--accent2))",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontSize: "0.65rem", fontWeight: 700, color: "#fff" }}>
                    {(user.name || user.email || "?")[0].toUpperCase()}
                  </div>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                                 maxWidth: 100, color: "var(--text)" }}>
                    {user.name || user.email}
                  </span>
                  <TierBadge tier={user.tier} lang={lang} />
                  <span style={{ color: "var(--text3)", fontSize: "0.6rem" }}>▾</span>
                </button>

                {userMenu && (
                  <div className="glass" style={{
                    position: "absolute", right: 0, top: "calc(100% + 8px)", width: 190,
                    borderRadius: 14, overflow: "hidden", boxShadow: "0 16px 48px rgba(0,0,0,.55)", zIndex: 50,
                  }}>
                    {[
                      { href: "/account", label: `👤 ${t.account}` },
                      ...(user.is_admin ? [{ href: "/admin/usage", label: `🔧 ${t.admin}` }] : []),
                    ].map((item) => (
                      <Link key={item.href} href={item.href} onClick={close}
                            style={{
                              display: "block", padding: "11px 16px", fontSize: "0.85rem",
                              color: "var(--text2)", textDecoration: "none", transition: "all 0.12s",
                            }}
                            onMouseEnter={(e) => { const el = e.currentTarget; el.style.background = "var(--border)"; el.style.color = "var(--text)"; }}
                            onMouseLeave={(e) => { const el = e.currentTarget; el.style.background = ""; el.style.color = "var(--text2)"; }}>
                        {item.label}
                      </Link>
                    ))}
                    <hr className="divider" style={{ margin: "0 12px" }} />
                    <button onClick={handleLogout}
                            style={{
                              width: "100%", textAlign: "left", padding: "11px 16px", fontSize: "0.85rem",
                              color: "var(--neg)", background: "none", border: "none", cursor: "pointer",
                              transition: "background 0.12s",
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--neg-bg)")}
                            onMouseLeave={(e) => (e.currentTarget.style.background = "")}>
                      ⏻ {t.logout}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: "flex", gap: 8 }}>
                <Link href="/auth/login" className="btn-secondary" style={{ fontSize: "0.82rem", padding: "6px 14px" }}>
                  {t.login}
                </Link>
                <Link href="/auth/register" className="btn-primary" style={{ fontSize: "0.82rem", padding: "6px 14px" }}>
                  {t.register}
                </Link>
              </div>
            )}
          </div>
        </div>
      </nav>
    </>
  );
}
