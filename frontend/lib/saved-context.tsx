"use client";

// Kaydedilenler (bookmarks, v2.2) — global "hangi haber_id'ler kayıtlı" seti.
// NewsCard'daki her yer imi ikonu bu context'i okur/yazar, tek tek fetch
// yapmaz. Kullanıcı çıkış yaparsa set temizlenir (auth-context.tsx'teki
// user null deseniyle aynı yaklaşım).

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "./auth-context";
import { fetchSavedArticles, saveArticleApi, unsaveArticleApi } from "./api";

interface SavedCtx {
  isSaved: (articleId: number) => boolean;
  toggleSaved: (articleId: number) => Promise<void>;
}

const SavedContext = createContext<SavedCtx>({
  isSaved: () => false,
  toggleSaved: async () => {},
});

export function SavedArticlesProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [savedIds, setSavedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!user) { setSavedIds(new Set()); return; }
    fetchSavedArticles()
      .then((articles) => setSavedIds(new Set(articles.map((a) => a.id))))
      .catch(() => {});
  }, [user]);

  const isSaved = useCallback((articleId: number) => savedIds.has(articleId), [savedIds]);

  const toggleSaved = useCallback(async (articleId: number) => {
    const wasSaved = savedIds.has(articleId);
    // İyimser (optimistic) güncelleme — API hata verirse aşağıda geri alınır.
    setSavedIds((cur) => {
      const next = new Set(cur);
      if (wasSaved) next.delete(articleId); else next.add(articleId);
      return next;
    });
    try {
      if (wasSaved) await unsaveArticleApi(articleId);
      else await saveArticleApi(articleId);
    } catch {
      setSavedIds((cur) => {
        const next = new Set(cur);
        if (wasSaved) next.add(articleId); else next.delete(articleId);
        return next;
      });
    }
  }, [savedIds]);

  return (
    <SavedContext.Provider value={{ isSaved, toggleSaved }}>
      {children}
    </SavedContext.Provider>
  );
}

export const useSavedArticles = () => useContext(SavedContext);
