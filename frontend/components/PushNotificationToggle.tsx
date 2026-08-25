"use client";

// Tarayıcı push bildirimi aç/kapat toggle'ı (v2.5). Mevcut "Anlık Uyarılar"
// (instant) e-posta aboneliğinin AYNI keyword listesini paylaşır — `enabled`
// prop'u o abonelik aktif değilse (Free tier veya frequency !== "instant")
// false gelir, toggle disabled + tooltip'li gösterilir. Tarayıcı push API'lerini
// desteklemiyorsa (canSpeak/TTS'teki client-detection deseniyle aynı) bileşen
// hiç render edilmez.

import { useEffect, useState } from "react";
import { isPushSupported, isPushSubscribed, subscribeToPush, unsubscribeFromPush } from "@/lib/webpush";

interface Props {
  vapidPublicKey: string;
  enabled: boolean;
  lockedReason: string;
  label: string;
  subscribedLabel: string;
  errorLabel: string;
}

export function PushNotificationToggle({
  vapidPublicKey, enabled, lockedReason, label, subscribedLabel, errorLabel,
}: Props) {
  const [supported, setSupported] = useState(false);
  const [subscribed, setSubscribed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    const ok = isPushSupported();
    setSupported(ok);
    if (ok) isPushSubscribed().then(setSubscribed).catch(() => {});
  }, []);

  if (!supported || !vapidPublicKey) return null;

  async function toggle() {
    setBusy(true);
    setError(false);
    try {
      if (subscribed) {
        await unsubscribeFromPush();
        setSubscribed(false);
      } else {
        await subscribeToPush(vapidPublicKey);
        setSubscribed(true);
      }
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ marginTop: 12 }}>
      <label
        style={{ display: "flex", alignItems: "center", gap: 8, opacity: enabled ? 1 : 0.5, cursor: enabled ? "pointer" : "not-allowed" }}
        title={!enabled ? lockedReason : undefined}
      >
        <input type="checkbox" checked={subscribed} disabled={!enabled || busy} onChange={toggle} />
        {subscribed ? subscribedLabel : label}
      </label>
      {error && <p style={{ color: "var(--danger, #e5484d)", fontSize: "0.85rem", marginTop: 4 }}>{errorLabel}</p>}
    </div>
  );
}
