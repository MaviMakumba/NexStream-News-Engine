"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import type { Tier } from "@/lib/types";
import { TierBadge } from "./TierBadge";
import { UI } from "@/lib/i18n";
import { THEME_LIST } from "@/lib/theme/registry";

export function Navbar() {
  const { user, logout } = useAuth();
  const { theme, lang, perf, setTheme, setLang, setPerf } = useSettings();
  const router = useRouter();
  const pathname = usePathname();
  const [userMenu, setUserMenu] = useState(false);
  const [settings, setSettings] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [visible, setVisible] = useState(true);
  const t = UI[lang];

  const close = () => { setUserMenu(false); setSettings(false); setMobileMenu(false); };

  // Aşağı kaydırınca navbar gizlenir, yukarı doğru en ufak bir kaydırmada
  // (veya sayfa başına yakınken) hemen geri gelir — sayfanın altındayken tema
  // değiştirmek için en tepeye kadar geri dönmeye gerek kalmasın diye.
  useEffect(() => {
    let lastY = window.scrollY;
    let ticking = false;

    function update() {
      const y = window.scrollY;
      if (userMenu || settings || mobileMenu || y < 80) {
        setVisible(true);
      } else if (y > lastY + 4) {
        setVisible(false);
      } else if (y < lastY - 4) {
        setVisible(true);
      }
      lastY = y;
      ticking = false;
    }

    function onScroll() {
      if (!ticking) {
        requestAnimationFrame(update);
        ticking = true;
      }
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [userMenu, settings, mobileMenu]);

  // Escape ile açık olan menüyü kapat — klavye kullanıcısı fareyle backdrop'a
  // tıklayamaz, bu olmadan menüyü kapatmanın tek yolu Tab ile başka yere gitmek olurdu.
  useEffect(() => {
    if (!userMenu && !settings && !mobileMenu) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [userMenu, settings, mobileMenu]);

  // Ekran mobil eşiğin (Tailwind `md`, 768px) üzerine büyüyünce mobil menüyü
  // otomatik kapat — yoksa panel görsel olarak gizlenir ama state açık kalır
  // ve arkasındaki görünmez backdrop tıklamaları yutmaya devam eder.
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    const handler = () => { if (mq.matches) setMobileMenu(false); };
    handler();
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  async function handleLogout() {
    await logout();
    close();
    router.push("/");
  }

  // Yönetim linki sadece admin rolündeki kullanıcıya görünür (v1.11).
  const navLinks = [
    { href: "/dashboard",        label: t.dashboard },
    { href: "/dashboard/search", label: t.search },
    ...(user?.is_moderator ? [{ href: "/admin/users", label: t.admin }] : []),
  ];

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");

  return (
    <>
      {(userMenu || settings || mobileMenu) && (
        <div style={{ position: "fixed", inset: 0, zIndex: 30 }} onClick={close} />
      )}

      <nav style={{
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        position: "sticky", top: 0, zIndex: 40,
        transform: visible ? "translateY(0)" : "translateY(-100%)",
        transition: "transform 0.25s ease",
      }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 20px",
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      height: 56, gap: 8 }}>

          {/* Logo */}
          <Link href="/" style={{ textDecoration: "none", marginRight: 8, flexShrink: 0 }}>
            <span className="font-display" style={{ fontSize: "1.15rem", fontWeight: 800 }}>
              <span style={{ color: "var(--text)" }}>Nex</span>
              <span className="gradient-text">Stream</span>
            </span>
          </Link>

          {/* Nav links — masaüstünde görünür, mobilde hamburger menüsüne taşınır */}
          <div className="hidden md:flex" style={{ alignItems: "center", gap: 2, flex: 1 }}>
            {navLinks.map((l) => (
              <Link key={l.href} href={l.href} aria-current={isActive(l.href) ? "page" : undefined} style={{
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

          {/* Right side (masaüstü) */}
          <div className="hidden md:flex" style={{ alignItems: "center", gap: 8, flexShrink: 0 }}>

            {/* Settings */}
            <div style={{ position: "relative" }}>
              <button onClick={() => { setSettings(!settings); setUserMenu(false); }}
                      title={t.settings} aria-label={t.settings}
                      aria-haspopup="true" aria-expanded={settings}
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
                                aria-pressed={active}
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
                              aria-pressed={lang === l}
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

                  <div className="section-label" style={{ margin: "16px 0 10px" }}>{t.perfLabel}</div>
                  <div style={{ display: "flex", gap: 6 }}>
                    {(["high", "low"] as const).map((p) => (
                      <button key={p} onClick={() => setPerf(p)}
                              aria-pressed={perf === p}
                              title={p === "low" ? t.perfLowDesc : t.perfHighDesc}
                              style={{
                                flex: 1, padding: "6px", borderRadius: 8, fontSize: "0.82rem",
                                cursor: "pointer", fontWeight: 600, transition: "all 0.15s",
                                border: `1px solid ${perf === p ? "var(--accent)" : "var(--border)"}`,
                                background: perf === p ? "var(--accent-soft)" : "rgba(0,0,0,.2)",
                                color: perf === p ? "var(--accent)" : "var(--text2)",
                              }}>
                        {p === "low" ? t.perfLow : t.perfHigh}
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
                        aria-haspopup="true" aria-expanded={userMenu}
                        aria-label={user.name || user.email}
                        style={{
                          display: "flex", alignItems: "center", gap: 8,
                          padding: "5px 12px", borderRadius: 8,
                          background: userMenu ? "var(--accent-soft)" : "var(--surface)",
                          border: `1px solid ${userMenu ? "var(--border2)" : "var(--border)"}`,
                          color: "var(--text)", cursor: "pointer", fontSize: "0.82rem",
                          transition: "all 0.15s", maxWidth: 280,
                        }}>
                  <div style={{ width: 22, height: 22, borderRadius: "50%", flexShrink: 0,
                                background: "linear-gradient(135deg, var(--accent), var(--accent2))",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontSize: "0.65rem", fontWeight: 700, color: "#fff" }}>
                    {(user.name || user.email || "?")[0].toUpperCase()}
                  </div>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                                 maxWidth: 100, flexShrink: 1, color: "var(--text)" }}>
                    {user.name || user.email}
                  </span>
                  <TierBadge tier={(user.effective_tier ?? user.tier) as Tier} lang={lang} isOwner={user.is_owner} />
                  <span style={{ color: "var(--text3)", fontSize: "0.6rem", flexShrink: 0 }}>▾</span>
                </button>

                {userMenu && (
                  <div className="glass" style={{
                    position: "absolute", right: 0, top: "calc(100% + 8px)", width: 190,
                    borderRadius: 14, overflow: "hidden", boxShadow: "0 16px 48px rgba(0,0,0,.55)", zIndex: 50,
                  }}>
                    {[
                      { href: "/account", label: `👤 ${t.account}` },
                      ...(user.is_moderator ? [{ href: "/admin/users", label: `🔧 ${t.admin}` }] : []),
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

          {/* Hamburger (mobil) — nav linkleri + hesap işlemlerini tek panelde toplar */}
          <button onClick={() => { setMobileMenu(!mobileMenu); setSettings(false); setUserMenu(false); }}
                  className="md:hidden"
                  aria-label={t.menu}
                  aria-expanded={mobileMenu}
                  style={{
                    background: mobileMenu ? "var(--accent-soft)" : "none",
                    border: `1px solid ${mobileMenu ? "var(--border2)" : "var(--border)"}`,
                    borderRadius: 8, color: mobileMenu ? "var(--accent)" : "var(--text3)",
                    cursor: "pointer", padding: "5px 10px", fontSize: "0.95rem",
                    transition: "all 0.15s", lineHeight: 1, flexShrink: 0,
                  }}>
            {mobileMenu ? "✕" : "☰"}
          </button>
        </div>
      </nav>

      {/* Mobil menü paneli — hamburger'a basınca nav linkleri + hesap/giriş işlemleri */}
      {mobileMenu && (
        <div className="flex md:hidden glass" style={{
          position: "fixed", top: 56, left: 0, right: 0, zIndex: 45,
          padding: 12, flexDirection: "column", gap: 4,
          maxHeight: "calc(100vh - 56px)", overflowY: "auto",
          boxShadow: "0 16px 48px rgba(0,0,0,.55)",
        }}>
          {navLinks.map((l) => (
            <Link key={l.href} href={l.href} onClick={close} style={{
              padding: "11px 14px", borderRadius: 10, fontSize: "0.9rem", fontWeight: 600,
              textDecoration: "none",
              color: isActive(l.href) ? "var(--accent)" : "var(--text)",
              background: isActive(l.href) ? "var(--accent-soft)" : "transparent",
            }}>
              {l.label}
            </Link>
          ))}

          <hr className="divider" style={{ margin: "6px 4px" }} />

          <div className="section-label" style={{ margin: "2px 4px 6px" }}>{t.theme}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "0 4px 8px" }}>
            {THEME_LIST.map((th) => {
              const active = theme === th.id;
              return (
                <button key={th.id} onClick={() => setTheme(th.id)}
                        title={t[th.labelKey]} aria-label={t[th.labelKey]} aria-pressed={active}
                        style={{
                          width: 34, height: 34, borderRadius: 8, cursor: "pointer",
                          display: "flex", alignItems: "center", justifyContent: "center",
                          fontSize: "0.95rem", color: active ? "var(--accent)" : "var(--text2)",
                          background: active ? "var(--accent-soft)" : "rgba(0,0,0,.2)",
                          border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
                        }}>
                  {th.icon}
                </button>
              );
            })}
          </div>
          <div style={{ display: "flex", gap: 6, padding: "0 4px 8px" }}>
            {(["TR", "EN"] as const).map((l) => (
              <button key={l} onClick={() => setLang(l)}
                      aria-pressed={lang === l}
                      style={{
                        flex: 1, padding: "7px", borderRadius: 8, fontSize: "0.82rem",
                        cursor: "pointer", fontWeight: 600, transition: "all 0.15s",
                        border: `1px solid ${lang === l ? "var(--accent)" : "var(--border)"}`,
                        background: lang === l ? "var(--accent-soft)" : "rgba(0,0,0,.2)",
                        color: lang === l ? "var(--accent)" : "var(--text2)",
                      }}>
                {l === "TR" ? "🇹🇷 TR" : "🇬🇧 EN"}
              </button>
            ))}
          </div>
          <div className="section-label" style={{ margin: "2px 4px 6px" }}>{t.perfLabel}</div>
          <div style={{ display: "flex", gap: 6, padding: "0 4px 8px" }}>
            {(["high", "low"] as const).map((p) => (
              <button key={p} onClick={() => setPerf(p)}
                      aria-pressed={perf === p}
                      style={{
                        flex: 1, padding: "7px", borderRadius: 8, fontSize: "0.82rem",
                        cursor: "pointer", fontWeight: 600, transition: "all 0.15s",
                        border: `1px solid ${perf === p ? "var(--accent)" : "var(--border)"}`,
                        background: perf === p ? "var(--accent-soft)" : "rgba(0,0,0,.2)",
                        color: perf === p ? "var(--accent)" : "var(--text2)",
                      }}>
                {p === "low" ? t.perfLow : t.perfHigh}
              </button>
            ))}
          </div>

          <hr className="divider" style={{ margin: "6px 4px" }} />

          {user ? (
            <>
              <Link href="/account" onClick={close} style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "10px 14px", borderRadius: 10, textDecoration: "none",
              }}>
                <div style={{ width: 26, height: 26, borderRadius: "50%", flexShrink: 0,
                              background: "linear-gradient(135deg, var(--accent), var(--accent2))",
                              display: "flex", alignItems: "center", justifyContent: "center",
                              fontSize: "0.68rem", fontWeight: 700, color: "#fff" }}>
                  {(user.name || user.email || "?")[0].toUpperCase()}
                </div>
                <span style={{ fontSize: "0.86rem", fontWeight: 600, color: "var(--text)",
                               overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                  {user.name || user.email}
                </span>
                <TierBadge tier={(user.effective_tier ?? user.tier) as Tier} lang={lang} isOwner={user.is_owner} />
              </Link>
              <button onClick={handleLogout} style={{
                textAlign: "left", padding: "11px 14px", borderRadius: 10, fontSize: "0.9rem",
                color: "var(--neg)", background: "none", border: "none", cursor: "pointer",
              }}>
                ⏻ {t.logout}
              </button>
            </>
          ) : (
            <div style={{ display: "flex", gap: 8, padding: "2px 4px 4px" }}>
              <Link href="/auth/login" onClick={close} className="btn-secondary"
                    style={{ flex: 1, justifyContent: "center", fontSize: "0.85rem" }}>
                {t.login}
              </Link>
              <Link href="/auth/register" onClick={close} className="btn-primary"
                    style={{ flex: 1, justifyContent: "center", fontSize: "0.85rem" }}>
                {t.register}
              </Link>
            </div>
          )}
        </div>
      )}
    </>
  );
}
