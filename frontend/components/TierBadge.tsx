import type { Tier } from "@/lib/types";

const MAP: Record<Tier, { labelTR: string; labelEN: string; style: React.CSSProperties }> = {
  free:       { labelTR: "Ücretsiz", labelEN: "Free",       style: { background: "rgba(120,130,150,.12)", color: "var(--text2)",  borderColor: "var(--border2)",   borderWidth: 1 } },
  pro:        { labelTR: "Pro",       labelEN: "Pro",        style: { background: "var(--accent-soft)",    color: "var(--accent)",  borderColor: "var(--accent-line)", borderWidth: 1 } },
  enterprise: { labelTR: "Kurumsal", labelEN: "Enterprise", style: { background: "var(--accent-soft)",    color: "var(--accent2)", borderColor: "var(--border2)",   borderWidth: 1 } },
};

const ICONS: Record<Tier, string> = { free: "○", pro: "◈", enterprise: "◆" };

export function TierBadge({ tier, lang = "TR" }: { tier: Tier; lang?: "TR" | "EN" }) {
  const t = MAP[tier] ?? MAP.free;
  return (
    <span className="badge" style={t.style}>
      {ICONS[tier]} {lang === "EN" ? t.labelEN : t.labelTR}
    </span>
  );
}
