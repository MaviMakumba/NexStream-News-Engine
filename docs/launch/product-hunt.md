# Product Hunt lansman materyali (taslak — 29 Eylül 2026)

Yayın kararı, sunucu/bütçe kararı netleşene kadar bekliyor (bkz. `docs/DURUM-DEGERLENDIRMESI.md`).
**Kural:** metindeki her iddia canlı ürünle doğrulanabilir olmalı; kullanıcı sayısı/gelir gibi
henüz olmayan şeyler ASLA yazılmaz.

## Ürün adı
NexStream

## Tagline (60 karakter sınırı)
- `Turkish & world news, analyzed by AI, in one live stream` (55)
- alternatif: `AI-analyzed news from 17+ sources, searchable by meaning` (56)

## Kısa açıklama (260 karakter sınırı)
Live news from Turkish and international outlets, enriched with AI: sentiment, entities, topic and a trust score on every story. Search by meaning, ask questions answered only from sources we actually track, and see how different outlets cover the same story.

## Maker'ın ilk yorumu
Hi PH 👋 I built NexStream because following Turkish news means juggling a dozen sites — and it is hard to tell what is a real story, who covered it, and whether outlets agree.

What it does today:
- **Live feed** from 17 Turkish and English sources, refreshed every 10 minutes
- **AI enrichment** per story: sentiment, people/organizations/locations, topic, short summary
- **Trust score** built from source credibility, content quality and how many independent outlets reported it
- **Hybrid search**: semantic (multilingual embeddings) + keyword, so "central bank rate decision" also finds the Turkish headline
- **Ask a question**: answers come only from tracked articles, with cited sources — and it says so when there is no evidence
- **Story clusters**: see how other outlets covered the same story
- Newsletter, browser push alerts on your keywords, a public REST API, PWA, 10 cinematic themes, Turkish/English UI

Stack for the curious: FastAPI (hexagonal architecture), PostgreSQL, ChromaDB, Redpanda, Groq LLMs, Next.js. It runs on a single small VPS.

Honest limitations: we only see RSS teasers (not full article text), so summaries are short; the free tier has daily API limits. I'd love feedback on what sources or topics to add next.

## Galeri (sıra)
1. Anasayfa hero + canlı akış (mobil ve masaüstü)
2. Bir haber kartı: trust score, entity çipleri, "Kaynaklar" paneli
3. Anlamsal arama sonuçları
4. "Soru sor" cevabı (kaynak atıflı)
5. Tema çeşitliliği (3 tema yan yana)

Ekran görüntüleri: `docs/screenshots/` (18 Eylül yenilemesinden sonra güncel). Mobil için
`frontend/e2e/states.spec.ts` ile 320/375/412 px görüntüleri üretilebilir.

## Yayın günü kontrol listesi
- [ ] Sunucu kararı verildi ve stabil (deploy sonrası `RestartCount` = 0)
- [ ] `test:mobile` yeşil, gerçek telefonda anasayfa + kayıt + arama denendi
- [ ] Yedek + geri yükleme testi tamam
- [ ] Salı-Perşembe, 00:01 PT yayın
- [ ] İlk 2 saat yorumlara yanıt
