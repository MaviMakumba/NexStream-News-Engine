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

export type LiveStatus = "connecting" | "live" | "disconnected";

const MAX_ITEMS = 8;
const RECONNECT_DELAY_MS = 4000;

export function useLiveFeed() {
  const [articles, setArticles] = useState<LiveArticle[]>([]);
  const [status, setStatus] = useState<LiveStatus>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  useEffect(() => {
    unmountedRef.current = false;

    function connect() {
      if (unmountedRef.current) return;
      setStatus("connecting");
      const wsUrl = BASE.replace(/^http/, "ws") + "/ws/feed";
      const ws = new WebSocket(wsUrl);
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

      ws.onclose = () => {
        if (unmountedRef.current) return;
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
  }, []);

  return { articles, status };
}
