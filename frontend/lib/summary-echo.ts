// Kart özeti başlığın yankısı mı? Bazı kaynakların RSS'i açıklama vermiyor (teaser =
// başlık; Sözcü'de son 500 haberin ~%44'ü) — LLM'in özetleyecek yeni bilgisi yok, başlığı
// aynen döndürüyor. Kartta aynı cümleyi iki kez göstermek yerine özeti saklarız.
// Prompt uzatmak çözmez (girdide bilgi yok) ve her Groq çağrısına token bindirir.
// Sınır: tam metin çekilene kadar (roadmap #18) yalnızca gösterim düzeyinde çözüm.

const norm = (s: string): string[] =>
  s.toLocaleLowerCase("tr").replace(/[^\p{L}\p{N}\s]/gu, " ").split(/\s+/).filter(Boolean);

export function isSummaryEcho(title: string, summary: string): boolean {
  const t = norm(title);
  const s = norm(summary);
  if (t.length === 0 || s.length === 0) return false;
  if (t.join(" ") === s.join(" ")) return true;
  // Özet başlığı içeriyor ama belirgin şekilde daha uzunsa yeni bilgi taşıyordur.
  if (s.length > Math.ceil(t.length * 1.35) + 2) return false;
  const sSet = new Set(s);
  const covered = t.filter((w) => sSet.has(w)).length;
  return covered / t.length >= 0.9;
}
