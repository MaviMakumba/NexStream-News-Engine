// Çalıştır: node --test lib/seo.test.ts
// 7 Eki 2026: Search Console "kullanıcı tarafından seçilen standart sayfa olmadan
// kopya" (anasayfa) uyarısı — sayfalarda canonical yoktu, sitemap'te ince auth
// sayfaları vardı.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import sitemap from "../app/sitemap.ts";

test("sitemap'te auth (giriş/kayıt) sayfaları yok — ince sayfalar dizine girmesin", () => {
  const urls = sitemap().map((e) => e.url);
  assert.equal(urls.some((u) => u.includes("/auth/")), false);
});

test("sitemap URL'leri tek kök alan adında ve sorgu parametresiz", () => {
  const urls = sitemap().map((e) => new URL(e.url));
  assert.equal(new Set(urls.map((u) => u.origin)).size, 1);
  assert.equal(urls.every((u) => u.search === ""), true);
});

test("kök layout her sayfa için canonical üretir (alternates.canonical)", () => {
  const layout = readFileSync(new URL("../app/layout.tsx", import.meta.url), "utf8");
  assert.match(layout, /alternates:\s*\{\s*canonical:\s*"\.\/"/);
});
