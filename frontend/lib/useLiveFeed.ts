"use client";

// /ws/feed WebSocket bağlantısını yönetir — reconnect + son N haberi tutar.
// Bkz. src/adapters/api/routers/websocket_router.py (backend) ve
// src/adapters/notifications/websocket_notifier.py (mesaj şekli).

import { useEffect, useRef, useState } from "react";
import { BASE } from "./api";

export interface LiveArticle {
  id: number;
  title: string;
  source: string;
  url: string;
  summary: string;
  sentiment_label?: string | null;
  topic?: string | null;
  created_at: string | null;
}

// "locked": Pro+ gerektiren özellik, ya çağıran taraf hiç bağlanmadı (enabled=false)
// ya da sunucu 1008 (policy violation — tier yetersiz) ile reddetti. İkisinde de
// sonsuz yeniden-bağlanma döngüsüne girmeyiz.
export type LiveStatus = "connecting" | "live" | "disconnected" | "locked";

const MAX_ITEMS = 8;
const RECONNECT_DELAY_MS = 4000;
const POLICY_VIOLATION_CLOSE_CODE = 1008;

/** @param enabled Pro+ olmayan kullanıcılar için false geçilip bağlantı hiç denenmemeli. */
export function useLiveFeed(enabled: boolean = true) {
  const [articles, setArticles] = useState<LiveArticle[]>([]);
  const [status, setStatus] = useState<LiveStatus>(enabled ? "connecting" : "locked");
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  useEffect(() => {
    if (!enabled) {
      setStatus("locked");
      return;
    }
    unmountedRef.current = false;

    function connect() {
      if (unmountedRef.current) return;
      setStatus("connecting");
      // BASE prod'da göreli bir yol olabilir (`/api`, bkz. NEXT_PUBLIC_API_URL —
      // nginx aynı origin üzerinden proxy'liyor). Göreli bir string doğrudan
      // `new WebSocket()`'e verilirse tarayıcı sayfanın şemasını (https) miras
      // alır ve "scheme ws/wss olmalı" SyntaxError'ı ATAR (senkron, try/catch'siz
      // yakalanmazsa efekt sessizce çöker) — 18 Ağu 2026'da canlıda böyle bulundu,
      // /ws/feed hiç bağlanamıyordu. BASE mutlak (http/https) değilse
      // window.location'dan ws(s):// açıkça inşa ediyoruz.
      const wsUrl = /^https?:\/\//.test(BASE)
        ? BASE.replace(/^http/, "ws") + "/ws/feed"
        : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}${BASE}/ws/feed`;
      let ws: WebSocket;
      try {
        ws = new WebSocket(wsUrl);
      } catch {
        setStatus("disconnected");
        timerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => setStatus("live");

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "article" && msg.data) {
            setArticles((prev) => [msg.data as LiveArticle, ...prev].slice(0, MAX_ITEMS));
          }
          // type: "ping" — sadece bağlantıyı canlı tutar, gösterilecek veri yok.
        } catch {
          // parse edilemeyen mesaj yok say
        }
      };

      ws.onclose = (event) => {
        if (unmountedRef.current) return;
        if (event.code === POLICY_VIOLATION_CLOSE_CODE) {
          // Sunucu tier yetersiz dedi — tekrar denemenin anlamı yok.
          setStatus("locked");
          return;
        }
        setStatus("disconnected");
        timerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      };

      ws.onerror = () => ws.close();
    }

    connect();

    return () => {
      unmountedRef.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [enabled]);

  return { articles, status };
}
