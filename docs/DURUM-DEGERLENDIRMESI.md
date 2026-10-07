# NexStream — Genel Durum Değerlendirmesi (SWOT + Öncelikler)

**Tarih:** 28 Eylül 2026 (20. oturum, prod sağlık taraması + PR #168-169 sonrası)
**Kural:** Bu dosya her oturum başında CLAUDE.md "YOL HARİTASI → 0. madde" üzerinden
gözden geçirilir. Bir madde tamamlanınca burada ~~üstü çizilir~~ + tarih/PR yazılır;
tablo bayatlarsa (ör. sunucu kararı verildiyse) yeni tarihli bir bölüm eklenir,
eskisi SİLİNMEZ — kullanıcı isteği: "kaybolmasınlar".

> **7 Eki 2026 güncellemesi:** 🔴 sunucu/bütçe kararı **gevşedi** — kredi $73,84, gerçek yakım ~$0,37/gün; asıl son tarih **28 Ocak 2027** (Free Plan bitince hesap kapanır; Paid'e geçilirse kalan kredi sonraki faturalara uygulanır, ~12 ay). Ek $100 aktivite kredisi muhtemelen alınmamış (konsolu kontrol et). Karar: Paid + Budgets uyarısı mı, Hetzner mı → Ocak başında. 🟠 Groq kotası: taşma katmanı canlı, 120b payı (150K/24sa) izlenecek; qwen `reasoning_effort: none` denemesi bekliyor. 🟠 Build'i CI'a taşıma (#28) hazır, merge bekliyor (PR #199). 🟡 Test geçerliliği ✅ (PR #198, merge bekliyor). 🟡 Search Console kopya uyarısı ✅ (canonical). 🔴 R2 offsite yedek + geri yükleme testi HÂLÂ açık. Yeni fikir (karar bekliyor): haber formatından daha "tutan" konsept — Haberle İngilizce / tahmin oyunu / izleme ajanı / alan radarı.

## Tek cümlede

Teknik olarak olgun, güvenli ve belgeli bir ürün — ama **kullanıcısı, geliri ve
Kasım ortasından sonraki bütçesi yok**. En büyük risk teknik değil, zamanlama.

## Ölçümler (28 Eyl 2026 itibarıyla)

| Metrik | Değer |
|---|---|
| Kayıtlı kullanıcı | 15 (son 10 günde 0 yeni) |
| Trafik | ~1.700 istek/gün (çoğu bot tarayıcısı) |
| İndeksli haber | ~27.150 |
| Günlük analiz | ~480-500 (failover öncesi TPD tavanı); failover sonrası izleniyor |
| Groq tüketimi (24 sa, failover öncesi) | ~250K token, ~484 başarılı çağrı, 702×429, çağrı başı ~517 token |
| Backend test | 1026 yeşil |
| Bağımlılık açığı | 0 (`pip-audit` + `npm audit`) |
| Host | t3.small 1,9 GB RAM, swap ~%70, disk %36 |
| AWS kredi | ~$0,93/gün yakım → **~Kasım 2026 ortası biter** |

## SWOT

| 💪 Güçlü yanlar | ⚠️ Zayıf yanlar |
|---|---|
| Hexagonal mimari gerçekten işe yarıyor (Groq failover domain'e dokunmadan yapıldı) | Tek t3.small (1,9 GB, swap %70), deploy sırasında OOM riski sürüyor (#28) |
| 1026 test, main'e her push'ta otomatik test + deploy | Analiz kapasitesi Groq ücretsiz kotasına bağlı (2 model, ~1000 analiz/gün tavanı) |
| Güvenlik: origin sadece Cloudflare'e açık, güvenlik günlüğü, açık 0, beg-bounty zararsız atlatıldı | Yedek 2 ay hiç alınmamıştı (28 Eyl düzeldi) — **offsite yok, geri yükleme hiç test edilmedi** |
| Zengin özellik: hibrit arama, RAG, push, bülten, 10 tema, TR/EN, PWA, admin | İçerik sadece RSS teaser'ı (30-80 kelime), tam metin yok → RAG/özet kalitesi sınırlı |
| $0/ay maliyet | Açık buglar: RAG alakasız kanıt (#13), `/api/api/v1` yol tesadüfü, `_stem_tr` kök çakışması, `/contact` maili spam'de (#26) |
| Güçlü dokümantasyon disiplini (CLAUDE.md + CHANGELOG + hafıza) | 16 Dependabot PR birikmiş; Tailwind 4 / TS 7 bump'ları build'i kırıyor |

| 🚀 Fırsatlar | 🔥 Tehditler |
|---|---|
| Hetzner CX33 (~$9-10/ay) 2-4× RAM → #28 büyük ölçüde gereksizleşir | **AWS kredisi ~Kasım ortası biter (28 Eyl'den ~6-7 hafta)** — karar yoksa site kapanır ya da fatura başlar |
| Doğrulanmış yeni kaynak adayları hazır (ekonomi/kripto, bilim, dünya, Reddit — sıfır ek kod) | Groq modelleri habersiz kaldırıyor/limit değiştiriyor (Ağustos'ta yaşandı) |
| Launch: LinkedIn metni + OG görseli hazır, Product Hunt eksik | AdSense "scraped content" ret riski (RSS agregatörü) |
| Trafik gelince AdSense (GVK 20/B, şirketsiz) | Tek sunucu = tek arıza noktası |
| Portfolyo değeri yüksek; gerçek prod hikâyeleri mülakat malzemesi | Public repo + commit geçmişindeki e-posta → hedef olma riski |

## Elimizde olanlar / olmayanlar

| ✅ Var | ❌ Yok |
|---|---|
| Canlı ürün + gerçek domain + TLS + CDN | Gerçek kullanıcı / trafik |
| Otomatik deploy, izleme yığını, alarmlar | Gelir (Stripe ertelendi, AdSense trafik bekliyor) |
| Günlük şifreli yedek (28 Eyl'den itibaren gerçekten) | Offsite yedek, test edilmiş geri yükleme |
| Güvenlik politikası, `security.txt`, olay günlüğü | Kasım sonrası bütçe / sunucu kararı |
| ~500 analizli haber/gün, 27k'lık arama indeksi | Tam makale metni, kullanıcı başına özel kaynak |

## Fazlalar (0 trafiğe göre ağır kalanlar)

| Bileşen | Maliyet | Karar |
|---|---|---|
| Prometheus + Grafana + Loki + Promtail | ~275 MB RAM (%15) | Kalsın (28 Eyl teşhisi Prometheus'la yapıldı); RAM darsa ilk kapatılacak |
| Redpanda (Kafka) | Bir container | Dakikalık birkaç mesaj için ağır ama ders/portfolyo gerekçesi geçerli — kalsın |
| Stripe/tier kodu | Bakım yükü | Kod hazır beklesin |
| 10 tema | Küçük | Ürün kimliği — kalsın |

Hüküm: hiçbiri şu an acil kesilmeyi gerektirmiyor; Hetzner'e geçilirse RAM baskısı kalkar.

## Öncelik tablosu

| Aciliyet | İş | Neden / ne zaman | Durum |
|---|---|---|---|
| 🔴 Acil | **Sunucu + bütçe kararı** (Hetzner CX33'e taşıma vs AWS ücretli) | Kredi ~6 hafta içinde biter; plan + prova 2-3 oturum → **Ekim başında başla** | Açık |
| 🔴 Acil | **R2 offsite yedek** | Kullanıcı CF'de bucket `nexstream-backups` + bucket'a scope'lu Object R/W token oluşturup Access Key ID / Secret / Account ID verecek; sonra rclone.conf + `RCLONE_REMOTE` (SSM) + test yedeği | Kullanıcıda |
| 🔴 Acil | **Yedekten geri yükleme testi** | Hiç test edilmemiş yedek yedek değildir — Hetzner taşıması bu testle birleştirilebilir | Açık |
| 🟠 Yüksek | 28 Eyl değişikliklerinin 2-3 günlük izlemesi | Model bazlı `nexstream_groq_tokens_total`, 429 sayısı, qwen vs 20b kalite (sentiment dağılımı, boş özet), 03:00 yedeğinin `/backups`'ta oluşması, `/home/ubuntu/chroma-migration-backup`'ın silinmesi, qwen 429 gövdesinde limit türü `?` → regex genişlet | Açık |
| 🟠 Yüksek | #28 build'i EC2 dışına (GHCR) | Sunucu kararıyla birlikte değerlendir (Hetzner'de aciliyeti düşer) | Açık |
| 🟠 Yüksek | Dependabot toplu güncelleme (16 PR) | Hepsi CI yeşil; tek deploy | Açık |
| 🟠 Yüksek | #30 güvenlik günlüğü denetimi | 18 Eyl'de verilen söz | Açık |
| 🟡 Orta | #14 clickbait özet prompt'u, #13 RAG kanıt alakası | Kullanıcıya görünen kalite | Açık |
| 🟡 Orta | Yeni kaynaklar (ekonomi/bilim/dünya) | Önce Groq kapasitesi izlensin | Açık |
| 🟡 Orta | `api.ts` `/api/api/v1` yolu, `_stem_tr` kök çakışması, #26 contact spam teşhisi | Bounded küçük buglar | Açık |
| 🟢 Düşük | Launch (Product Hunt/LinkedIn), AdSense ön hazırlığı, Reddit denemesi | Sunucu kararından sonra | Açık |
| 🟢 Düşük | #18 tam metin, #3 özel kaynak, #2 Stripe | Büyük mimari/ürün kararları | Açık |

## Önerilen sıra

1. **Sonraki oturum:** R2 yedek + 28 Eyl izleme sonuçları + Dependabot toplu güncelleme.
2. **Ekim ilk yarısı:** Hetzner taşıma planı + provası (geri yükleme testi bunun içinde).
3. **Taşıma sonrası:** kalite (#14, #13) → yeni kaynaklar → launch.


---

## 30 Eylül 2026 güncellemesi (21. oturum sonu) — eski tablo SİLİNMEDİ, durumlar burada

| İş | Durum (30 Eyl) |
|---|---|
| 🔴 Sunucu + bütçe kararı | **AÇIK, Kasım ortası!** (Hetzner CX33 planı+provası Ekim başında başlamalı) |
| 🔴 R2 offsite yedek | **AÇIK** — kullanıcı CF bucket `nexstream-backups` + Object R/W token verecek |
| 🔴 Yedekten geri yükleme testi | **AÇIK** — Hetzner taşımasıyla birleştirilebilir |
| 🟠 28 Eyl değişikliklerinin izlenmesi | ✅ temiz (17 kaynak çalışıyor, boş özet %0,5, restart/OOM 0, günlük haber ~480→1045). `chroma-migration-backup` (83 MB) **silinmedi**, kullanıcı onayı bekliyor |
| 🟠 #28 build'i GHCR'a taşıma | **Şimdilik gereksiz** (18 Eyl'den beri host sağlıklı: yük 0,16, OOM yok); sunucu kararıyla yeniden değerlendir |
| 🟠 Dependabot toplu | ✅ 16 PR tek dalda deploy edildi (#23 Tailwind 4 / #18 TS 7 kapsam dışı, hâlâ açık) |
| 🟠 #30 güvenlik günlüğü denetimi | ✅ 6 yeni olay tipi, admin sayfası UX, Stripe tier değişimi |
| 🟡 #14 özet yankısı | ✅ UI'da gizleme (kök neden: kaynak RSS'inde açıklama yok) |
| 🟡 #13 RAG kanıt alakası | ✅ özel isim doğrulaması (fail-open) |
| 🟡 `api.ts` yolu, `_stem_tr` | ✅ |
| 🟡 #26 `/contact` maili spam | **Teyit bekliyor** — hoş geldin maili spam'e düşmedi (Resend yolu); `/contact` formunu bir kez deneyip gelen kutusuna bakmak gerekir |
| 🟡 Yeni kaynaklar | ✅ 11 kaynak + tavanlar (S2); ilk gerçek ingest izlenecek |
| 🟢 AdSense ön hazırlığı, Product Hunt | ✅ çerez kategorileri, `docs/launch/product-hunt.md` |
| 🟢 #18 tam metin, #3 özel kaynak, #2 Stripe | Ertelemeyi koru (kullanıcı kararı) |
| **YENİ** İçerik/tazelik/çok dillilik (B+D) | S1 ✅ S2 ✅ · **sıradaki S3 → S4 → S5** · S6 iptal · sonra C (UI yenileme) |
| **YENİ** Mobil kullanılabilirlik | ✅ tarama + 120 testlik CI paketi; **gerçek telefonda elle deneme** kullanıcıda |
