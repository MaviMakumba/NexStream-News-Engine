// Çalıştır: node --test lib/summary-echo.test.ts   (Node >= 22.6 tip soyma; CI'da Node 22)
import { test } from "node:test";
import assert from "node:assert/strict";
import { isSummaryEcho } from "./summary-echo.ts";

test("özet başlığın aynısı ya da sonuna nokta eklenmişi: yankı", () => {
  assert.equal(isSummaryEcho("9 belediye başkanı AKP'ye katıldı", "9 belediye başkanı AKP'ye katıldı."), true);
  assert.equal(isSummaryEcho("Kavga edenlerin arasına araçla daldı! Çok sayıda yaralı var", "Kavga edenlerin arasına araçla daldı! Çok sayıda yaralı var"), true);
});

test("özet başlığa yeni bilgi katıyorsa yankı DEĞİL", () => {
  assert.equal(isSummaryEcho(
    "Fatma Betül Sayan Kaya'nın mal varlıklarının dondurulması istendi",
    "Fon soruşturması kapsamında Fatma Betül Sayan Kaya ve eşi İlyas Kaya'nın mal varlıklarının dondurulması istendi."), false);
  assert.equal(isSummaryEcho("İSKOÇYA İSVİÇRE MAÇI HANGİ KANALDA?", "İskoçya, Uluslar B Ligi 1. Grup'ta İsviçre'yi konuk ediyor ve her iki takım da gol arayacak."), false);
});

test("Türkçe büyük/küçük harf ve noktalama farkı yankıyı gizlemez", () => {
  assert.equal(isSummaryEcho("İSRAİL'DE ALARM: Netanyahu toplanıyor", "İsrail'de alarm: Netanyahu toplanıyor!"), true);
});

test("boş ya da çok kısa girdilerde güvenli: özet varsa gösterilir", () => {
  assert.equal(isSummaryEcho("Başlık", ""), false);
  assert.equal(isSummaryEcho("", "Özet metni burada"), false);
  assert.equal(isSummaryEcho("Kısa", "Kısa"), true);           // birebir aynı
  assert.equal(isSummaryEcho("Kısa başlık", "Tamamen farklı bir cümle var"), false);
});

test("başlık kelimelerinin çoğu var ama özet belirgin şekilde daha uzunsa yankı DEĞİL", () => {
  assert.equal(isSummaryEcho("Merkez Bankası faizi sabit tuttu",
    "Merkez Bankası faizi sabit tuttu; karar metninde enflasyon görünümüne ve kredi büyümesine dikkat çekildi, gelecek toplantı için ipucu verilmedi."), false);
});
