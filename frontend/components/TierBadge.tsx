import type { Tier } from "@/lib/types";

const MAP: Record<Tier, { labelTR: string; labelEN: string; style: React.CSSProperties }> = {
  free:       { labelTR: "Ücretsiz", labelEN: "Free",       style: { background: "rgba(100,116,139,.12)", color: "#94a3b8",  borderColor: "rgba(100,116,139,.3)",  borderWidth: 1 } },
  pro:        { labelTR: "Pro",       labelEN: "Pro",        style: { background: "rgba(34,211,238,.10)",  color: "#22d3ee",  borderColor: "rgba(34,211,238,.3)",   borderWidth: 1 } },
  enterprise: { labelTR: "Kurumsal", labelEN: "Enterprise", style: { background: "rgba(167,139,250,.10)", color: "#a78bfa",  borderColor: "rgba(167,139,250,.3)",  borderWidth: 1 } },
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
