"use client";

// Admin müşteri/kullanıcı listesi sayfası — tüm kayıtlı kullanıcılar, tier'ları
// ve GERÇEK ödeme durumu (is_paying = stripe_customer_id dolu mu). BILLING_DEV_MODE'daki
// tek-tık tier yükseltmeleri stripe_customer_id'yi hiç yazmaz, bu yüzden bu sütun
// "dev-mode'da yükseltilmiş" ile "gerçekten ödeyen" ayrımını gösterir.
//
// Yetki (v1.13): moderator+admin listeyi görebilir; rolü sadece admin değiştirebilir
// (backend PATCH /admin/users/{id}/role require_admin ister) — moderator için rol
// sütunu salt-okunur rozet olarak gösterilir.

import { useCallback, useEffect, useState } from "react";
import { fetchUsers, updateUserRole } from "@/lib/api";
import type { AdminUser, Role } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { useSettings } from "@/lib/settings-context";
import { TierBadge } from "@/components/TierBadge";
import { UI } from "@/lib/i18n";

const TIER_VALUES = ["", "free", "pro", "enterprise"];
const ROLE_VALUES: Role[] = ["user", "moderator", "admin"];

const ROLE_STYLE: Record<Role, React.CSSProperties> = {
  user:      { background: "rgba(120,130,150,.12)", color: "var(--text2)", borderColor: "var(--border2)" },
  moderator: { background: "var(--neu-bg)",          color: "var(--neu)",  borderColor: "var(--neu)" },
  admin:     { background: "var(--accent-soft)",     color: "var(--accent)", borderColor: "var(--accent-line)" },
};

export default function AdminUsersPage() {
  const { user } = useAuth();
  const { lang } = useSettings();
  const t = UI[lang];
  const roleLabel: Record<Role, string> = { user: t.roleUser, moderator: t.roleModerator, admin: t.roleAdmin };
  const isModerator = Boolean(user?.is_moderator);
  const isAdmin = Boolean(user?.is_admin);

  const [apiKey,   setApiKey]   = useState("");
  const [tier,     setTier]     = useState("");
  const [total,    setTotal]    = useState(0);
  const [users,    setUsers]    = useState<AdminUser[]>([]);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");
  const [loaded,   setLoaded]   = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);

  const load = useCallback(async (key?: string) => {
    // Moderator/admin oturumu varsa anahtar gerekmez (cookie otomatik taşınır); yoksa girilen anahtar kullanılır.
    const creds = isModerator ? {} : { apiKey: key ?? apiKey };
    if (!isModerator && !(creds.apiKey ?? "").trim()) return;
    setLoading(true); setError("");
    try {
      const data = await fetchUsers(creds, 100, 0, tier || undefined);
      setUsers(data.items);
      setTotal(data.total);
      setLoaded(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.accessDenied);
    } finally {
      setLoading(false);
    }
  }, [isModerator, apiKey, tier, t.accessDenied]);

  // Moderator/admin rolü varsa sayfa açılır açılmaz yükle (tier filtresi değişince de).
  useEffect(() => {
    if (isModerator) load();
  }, [isModerator, tier, load]);

  async function handleRoleChange(targetId: number, role: Role) {
    const creds = isModerator ? {} : { apiKey };
    setSavingId(targetId); setError("");
    try {
      await updateUserRole(creds, targetId, role);
      setUsers((prev) => prev.map((u) => (u.id === targetId ? { ...u, role } : u)));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.roleUpdateError);
    } finally {
      setSavingId(null);
    }
  }

  const payingCount = users.filter((u) => u.is_paying).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Auth bar: moderator+admin'e bilgi notu, diğerlerine API key girişi */}
      <div className="card" style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end" }}>
        {isModerator ? (
          <div style={{ flex: "1 1 240px", fontSize: "0.84rem", color: "var(--pos)", paddingBottom: 6 }}>
            ✓ {t.adminAsUser}
          </div>
        ) : (
          <div style={{ flex: "1 1 240px" }}>
            <label className="label">{t.adminKey}</label>
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                   onKeyDown={(e) => e.key === "Enter" && load()}
                   className="input" placeholder="dev-key-change-me" />
          </div>
        )}
        <div>
          <label className="label">{t.tierFilter}</label>
          <select value={tier} onChange={(e) => setTier(e.target.value)}
                  className="input" style={{ width: 160, fontSize: "0.84rem" }}>
            {TIER_VALUES.map((v) => <option key={v} value={v}>{v ? v : t.allTiers}</option>)}
          </select>
        </div>
        <button onClick={() => load()} disabled={loading || (!isModerator && !apiKey.trim())} className="btn-primary">
          {loading ? t.loadingShort : t.show}
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--neg-bg)", border: "1px solid var(--neg)", borderRadius: 12,
                      padding: "12px 16px", fontSize: "0.84rem", color: "var(--neg)" }}>⚠ {error}</div>
      )}

      {loaded && (
        <>
          {/* KPI cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
            {[
              { value: total.toLocaleString(),       label: t.totalUsers, color: "var(--accent)" },
              { value: payingCount.toLocaleString(),  label: t.payingUsers, color: "var(--pos)" },
            ].map((kpi) => (
              <div key={kpi.label} className="card" style={{ textAlign: "center" }}>
                <div style={{ fontSize: "1.8rem", fontWeight: 800, color: kpi.color, lineHeight: 1.2, marginBottom: 4 }}>
                  {kpi.value}
                </div>
                <div className="section-label">{kpi.label}</div>
              </div>
            ))}
          </div>

          {/* Table */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.84rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {[t.colEmail, t.colTier, t.colRole, t.colStatus, t.colPaying, t.colJoined].map((h) => (
                      <th key={h} style={{
                        padding: "14px 20px", textAlign: "left",
                        color: "var(--text3)", fontWeight: 700, textTransform: "uppercase",
                        letterSpacing: "0.06em", fontSize: "0.7rem",
                      }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} style={{ borderBottom: "1px solid var(--border)", transition: "background 0.1s" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--border)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "")}>
                      <td style={{ padding: "12px 20px", color: "var(--text)" }}>{u.email}</td>
                      <td style={{ padding: "12px 20px" }}>
                        <TierBadge tier={u.tier as "free" | "pro" | "enterprise"} lang={lang} />
                      </td>
                      <td style={{ padding: "12px 20px" }}>
                        {isAdmin ? (
                          <select
                            value={u.role}
                            disabled={savingId === u.id || u.id === user?.id}
                            onChange={(e) => handleRoleChange(u.id, e.target.value as Role)}
                            className="input"
                            style={{
                              width: "auto", padding: "4px 10px", fontSize: "0.76rem", fontWeight: 600,
                              ...ROLE_STYLE[u.role],
                            }}
                            title={u.id === user?.id ? t.roleUpdateError : undefined}
                          >
                            {ROLE_VALUES.map((r) => <option key={r} value={r}>{roleLabel[r]}</option>)}
                          </select>
                        ) : (
                          <span className="badge" style={ROLE_STYLE[u.role]}>{roleLabel[u.role]}</span>
                        )}
                      </td>
                      <td style={{ padding: "12px 20px" }}>
                        {u.is_active ? (
                          <span className="badge" style={{ background: "var(--pos-bg)", color: "var(--pos)", borderColor: "var(--pos)" }}>
                            ● {t.activeStatus}
                          </span>
                        ) : (
                          <span className="badge" style={{ background: "var(--neu-bg)", color: "var(--neu)", borderColor: "var(--neu)" }}>
                            {t.inactiveStatus}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "12px 20px" }}>
                        {u.tier === "free" ? (
                          <span style={{ color: "var(--text3)" }}>—</span>
                        ) : u.is_paying ? (
                          <span className="badge" style={{ background: "var(--pos-bg)", color: "var(--pos)", borderColor: "var(--pos)" }}>
                            {t.payingReal}
                          </span>
                        ) : (
                          <span className="badge" style={{ background: "var(--neu-bg)", color: "var(--neu)", borderColor: "var(--neu)" }}>
                            {t.payingDev}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "12px 20px", color: "var(--text3)", fontFamily: "monospace", fontSize: "0.78rem" }}>
                        {new Date(u.created_at).toLocaleDateString(lang === "TR" ? "tr-TR" : "en-US")}
                      </td>
                    </tr>
                  ))}
                  {users.length === 0 && (
                    <tr>
                      <td colSpan={6} style={{ padding: "40px", textAlign: "center", color: "var(--text3)" }}>
                        {t.noUsers}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
