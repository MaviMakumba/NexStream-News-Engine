"use client";

// /ws/feed bağlantısını dashboard segmenti boyunca TEK yerden paylaşır —
// LiveTicker ve dashboard/page.tsx'in aynı veriyi ayrı ayrı bağlantı açmadan
// tüketmesini sağlar. Provider DashboardShell'de (dashboard/layout.tsx) yaşar,
// bu yüzden /dashboard ↔ /dashboard/search arası gezinirken bağlantı kopmaz.

import { createContext, useContext } from "react";
import { useLiveFeed, LiveArticle, LiveStatus } from "./useLiveFeed";
import { useAuth } from "./auth-context";

interface LiveFeedCtx {
  articles: LiveArticle[];
  status: LiveStatus;
}

const LiveFeedContext = createContext<LiveFeedCtx>({ articles: [], status: "locked" });

export function LiveFeedProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const et = user?.effective_tier ?? user?.tier;
  const isPro = et === "pro" || et === "enterprise";
  const feed = useLiveFeed(isPro);
  return <LiveFeedContext.Provider value={feed}>{children}</LiveFeedContext.Provider>;
}

export const useLiveFeedContext = () => useContext(LiveFeedContext);
