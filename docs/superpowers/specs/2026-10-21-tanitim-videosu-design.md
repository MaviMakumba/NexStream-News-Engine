# Tanıtım videosu — tasarım (21 Ekim 2026)

Onaylı storyboard'un yazılı hâli (storyboard v2 + kullanıcının son iki notu). Kodu `promo/`.

## Amaç
Siteye ilk gelen ziyaretçiye 1 dakikanın altında "bu ne işe yarıyor, bana ne katar"ı
göstermek; ikincil kitle GitHub'da projeyi inceleyen geliştirici/işveren. Onaydan sonra
ana sayfaya (kapak + oynat butonu) ve README'ye (TR bölümüne TR, EN bölümüne EN) eklenecek.

## Kararlar (kullanıcının)
- 4 çıktı: TR/EN × yatay 16:9 (1920×1080) / dikey 9:16 (1080×1920). Yatay zorunlu, dikey aynı hikâyenin mobil kurgusu.
- Seslendirme YOK; ekranda kısa yazılar + hafif ritmik müzik + ses efektleri.
- Görüntüler sitenin GERÇEK arayüzünden (birebir tasarım); hayali çizim yok.
- Kaynak adları "Kaynak A/B/…" ("Source A/B/…"), başlıklar uydurma ve nötr (gerçek kişi adı yok) — telif/itibar riski.
- E-posta sahnesi Gmail'e BENZEYEN jenerik istemci; Google logosu/markası yok.
- Temalar haber sayfası açıkken hızlı geçişle gösterilir.
- Haber kartı: önce tüm rozet/butonlar birlikte etiketlenir, sonra sırayla İlgili → Kaynaklar → Dinle → Kaydet → Sor tıklanıp sonucu gösterilir.
- Logo sahnesinde ve kapanışta yeşil "N" uygulama ikonu (favicon) wordmark'la birlikte; slogan "Haberi okuma. Anla." DEĞİL, daha güçlü bir slogan.

## Sahne akışı (57 sn, 30 fps; sınırlar müziğin vuruş ızgarasına oturur, 129 BPM)
| sn | sahne |
|----|-------|
| 0–4 | Kanca: uydurma başlıklar uçuşur, donar — "Her gün yüzlerce haber. Hangisi gerçekten önemli?" |
| 4–7,7 | Drop: başlıklar çekilir → N ikonu + NexStream + slogan |
| 7,7–13,3 | Haberler sayfasında 10 tema, vuruş başına bir kesme (gerçek canvas efektleri) |
| 13,3–18,9 | Akışa dalış: CANLI şerit, yeni kart düşer, piyasa şeridi/gündem/filtre etiketleri |
| 18,9–30 | Haber kartına zoom + butonlar |
| 30–35,6 | Soru Sor (karttaki Sor'dan köprü), kaynak numaraları vurgulu |
| 35,6–40,2 | Semantik arama, yazma + % eşleşme |
| 40,2–45,8 | Hesabım yukarıdan aşağı (gerçek sayfa), bülten tercihinde yavaşlar |
| 45,8–50,4 | Jenerik posta istemcisinde gerçek bülten şablonu (`_digest_html`) |
| 50,4–57 | Özellik çipleri → N + logo + nexstreamnews.com + "Ücretsiz başla" (müziğin son vuruşunda) |

## Builder'ın kararları (benim, değiştirilebilir)
- **Slogan:** TR "Gürültüyü kes. Haberin özünü yakala." / EN "Cut the noise. Catch the story." — kancadaki "gürültü" ile bağlanıyor.
- **Araç:** Remotion 4 (`promo/`, ayrı package.json; frontend'e bağımlılık eklemez).
- **Görüntü üretimi:** `promo/capture/` — Playwright, `next start` + taklit API (mobil testlerdeki desen); Playwright `clock` ile zaman kontrollü kare kare kayıt (tema canvas efektleri deterministik), eleman konumları manifest JSON'a yazılır, Remotion etiket/imleç yerlerini oradan alır. Taklit veri yalnız `promo/capture/`'da.
- **Müzik:** Mixkit "Digital Clouds" (Alejandro Magaña, Mixkit Stock Music Free License — ticari kullanım, atıf gerekmez, ham dosya yeniden dağıtılamaz) → mp3 repoya GİRMEZ, `promo/scripts/fetch-music.mjs` indirir. Parça 25,81 sn'den başlar (29,81'deki swell = video 4,0), 74,39'da kendi 89,26'sına (son cümle) bağlanır; son vuruş 95,29 = video 54,6.
- **Ses efektleri:** `promo/scripts/make_sfx.py` ile sentezlenir (lisans sorunu yok, repoya girer).
- **Çıktı:** H.264 + AAC MP4, her biri ≤ 10 MB (GitHub ücretsiz yükleme sınırı); kapak JPG'leri.

## Kapsam dışı
Seslendirme, gerçek kaynak adları/başlıkları, admin paneli, Remotion'u CI'a bağlamak.
Siteye/README'ye ekleme ayrı adım — kullanıcı videoyu onayladıktan sonra.
