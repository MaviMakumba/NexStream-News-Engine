"use client";

import { useSettings } from "@/lib/settings-context";
import { SENTIMENT_LABELS } from "@/lib/i18n";

const STYLES: Record<string, React.CSSProperties> = {
  Positive: { background: "var(--pos-bg)", color: "var(--pos)", borderColor: "var(--pos)", borderWidth: 1 },
  Negative: { background: "var(--neg-bg)", color: "var(--neg)", borderColor: "var(--neg)", borderWidth: 1 },
  Neutral:  { background: "var(--neu-bg)", color: "var(--neu)", borderColor: "var(--neu)", borderWidth: 1 },
};

export function SentimentBadge({ label }: { label?: string | null }) {
  const { lang } = useSettings();
  if (!label || !STYLES[label]) return null;
  return (
    <span className="badge" style={STYLES[label]}>
      {SENTIMENT_LABELS[lang]?.[label] ?? label}
    </span>
  );
}
