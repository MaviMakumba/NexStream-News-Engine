// Tarayıcı push abonelik yardımcıları — Notification permission + Service
// Worker PushManager (v2.5). Tarayıcı desteklemiyorsa (Notification/
// serviceWorker/PushManager yok) sessizce false döner, hata FIRLATMAZ —
// çağıran taraf (PushNotificationToggle) buna göre kendini gizler.

import { subscribeToPushApi, unsubscribeFromPushApi } from "./api";

export function isPushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "Notification" in window &&
    "serviceWorker" in navigator &&
    "PushManager" in window
  );
}

function urlBase64ToUint8Array(base64: string): BufferSource {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const base64Safe = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64Safe);
  // TS'in Uint8Array<ArrayBufferLike> ile BufferSource'un ArrayBuffer-only
  // varyantı arasındaki katı tip uyuşmazlığı — çalışma zamanında burada
  // her zaman gerçek bir ArrayBuffer var (SharedArrayBuffer hiç mümkün değil,
  // Uint8Array.from() yeni bir dizi oluşturur), o yüzden güvenli bir assertion.
  return Uint8Array.from(raw.split("").map((c) => c.charCodeAt(0))) as BufferSource;
}

export async function isPushSubscribed(): Promise<boolean> {
  if (!isPushSupported()) return false;
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  return sub !== null;
}

export async function subscribeToPush(vapidPublicKey: string): Promise<void> {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Bildirim izni verilmedi.");

  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  });
  const json = sub.toJSON();
  try {
    await subscribeToPushApi(json.endpoint!, json.keys!.p256dh, json.keys!.auth);
  } catch (err) {
    await sub.unsubscribe();
    throw err;
  }
}

export async function unsubscribeFromPush(): Promise<void> {
  if (!isPushSupported()) return;
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  if (!sub) return;
  const endpoint = sub.endpoint;
  await sub.unsubscribe();
  await unsubscribeFromPushApi(endpoint);
}
