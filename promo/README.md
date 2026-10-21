# NexStream tanıtım videosu

57 saniyelik tanıtım videosu: TR/EN × yatay (1920×1080) / dikey (1080×1920). Görüntüler
sitenin **gerçek arayüzünden** kurgusal veriyle üretilir, video [Remotion](https://www.remotion.dev/)
ile kodlanır. Tasarım kararları: `docs/superpowers/specs/2026-10-21-tanitim-videosu-design.md`.

## Yeniden üretmek

```powershell
# 1) frontend'i derleyip 3100'de aç (frontend Docker container'ı KAPALIYKEN — bkz. CLAUDE.md)
cd frontend; npm run build; npx next start --port 3100

# 2) ayrı terminalde
cd promo
npm install
node scripts/fetch-music.mjs                      # müzik (repoya girmez, lisans)
..\venv\Scripts\python.exe scripts\make_sfx.py    # ses efektleri (zaten repoda; değiştirirsen)
npm run capture                                   # public/captures/<dil>-<biçim>/ (~4 dk)
npm run studio                                    # önizleme (tarayıcıda)
npm run render:all                                # out/*.mp4 + kapaklar (~30 dk)
```

Playwright/Remotion için ayrı tarayıcı indirmek istemezsen kurulu bir Chromium göster:
`$env:PW_CHROME="$env:LOCALAPPDATA\ms-playwright\chromium-1234\chrome-win64\chrome.exe"`.
Tek kare önizleme: `node scripts/stills.mjs Promo-TR-desktop 205,600,1700`.

## Nasıl çalışıyor

- **`capture/capture.mjs`** — `next start` + taklit API (`capture/mock-data.mjs`, mobil e2e
  testlerindeki desen) + taklit `/ws/feed`. Her sahnenin durumlarını (ör. kart → İlgili açık →
  Kaynaklar açık → Dinle → Kaydet) görüntü olarak alır ve elemanların konumunu
  `manifest.json`'a yazar; Remotion etiket/imleç yerlerini oradan hesaplar, yani arayüz
  değişince yeniden `npm run capture` yeterli. Tema efektleri (Matrix yağmuru vb.)
  Playwright `clock` ile kare kare, deterministik yakalanır. Bülten maili gerçek şablondan
  (`email_adapter._digest_html`, `capture/digest.py`) üretilir.
- **`src/timeline.ts`** — tek zaman kaynağı. Sahne sınırları müziğin vuruş ızgarasına
  (129 BPM) oturur; müzik parçanın kendi son cümlesine bağlanır, son vuruşu kapanış logosuna düşer.
- **`src/copy.ts`** — videodaki tüm metin, dil başına bir blok.
- **`src/formats.ts`** — yatay/dikey farkları (yazı ölçüleri, alt yazı yeri, kameranın güvenli alanı).

## Bilinen tuzak

`fullPage: true` ekran görüntüsü KULLANMA: Playwright tam sayfa çekerken dokunmatik
emülasyonu düşürüyor, mobilde `pointer: coarse` boşlukları kaybolup içerik ölçülen
konumlardan ~110 px kayıyor. Uzun sayfalar görünüm büyütülerek çekilir (`tallViewport`).
Teşhis için: `node capture/capture.mjs TR mobile debug` (ölçülen kutuları sayfaya çizer).

## Lisanslar

- Müzik: "Digital Clouds" — Alejandro Magaña (A. M.), [Mixkit](https://mixkit.co/free-stock-music/tag/technology/),
  Mixkit Stock Music Free License (videoda ticari kullanım serbest, atıf gerekmez; ham dosya
  yeniden dağıtılamaz → `public/music/` git'e girmez).
- Ses efektleri: `scripts/make_sfx.py` ile sentezlendi (bu projeye ait).
- Videodaki haber başlıkları ve kaynak adları ("Kaynak A/B…") kurgusaldır.
