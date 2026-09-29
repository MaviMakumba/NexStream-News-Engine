# S2 — Tazelik-öncelikli alım, kaynak portföyü ve günlük tavanlar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (Native seçildi). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Groq kotası darken analiz bütçesi eskiye değil EN TAZE habere gitsin; 11 yeni kaynak eklenirken konu dengesi ve toplam günlük hacim tavanlarla korunsun.

**Architecture:** (1) Saf domain politikası `select_for_analysis` — yaş süzgeci + tazelik sıralaması + günlük/çalıştırma bütçesi. (2) Kaynaklar `language` / `focus_topic` / `daily_cap` bildirir; env ile `SOURCE_DAILY_CAPS` geçersiz kılar. (3) `update_news_from_source` kalan günlük bütçeyi `count_articles_since` ile hesaplayıp politikaya verir. (4) `BaseRssScraper` "önce hepsini ayrıştır, tarihe göre sırala, sonra dilimle" der (tarih sırasız feed'ler taze haberi kaçırıyordu). (5) Kapasite modeli testle kilitlenir: tüm tavanların toplamı ≤ 950/gün.

**Tech Stack:** Python 3.13 / pytest / httpx + BeautifulSoup / prometheus_client.

**Spec:** `docs/superpowers/specs/2026-09-29-icerik-genisletme-cok-dillilik-tazelik-design.md` §4.2, §5.

## Global Constraints

- Analiz sırası: **en yeni yayın tarihi önce**; `max_article_age_hours` (varsayılan **48**) üstündeki haber HİÇ analiz edilmez; yayın tarihi olmayan haber elenmez ama tarihli olanların arkasına düşer.
- Günlük tavan = son 24 saatte `news_articles`'a kaydedilen haber sayısına karşı; tavan dolunca kaynak o tur atlanır (`nexstream_source_capped_total{source}`).
- Tüm tavanların toplamı **≤ 950** (kapasite modeli, spec §5); yeni kaynak eklerken test kırılırsa başka bir kaynağın tavanı düşürülür — testin tavanı gevşetilmez.
- `focus_topic` ya `None` (genel kaynak) ya da `src/domain/topics.py::VALID_TOPIC_IDS` içinde; Politics ve Other dışındaki her konunun en az bir odaklı kaynağı olmalı.
- Yeni kaynak = scraper sınıfı + registry + `credibility.py` + `settings.scrape_sources` + iki compose dosyası (`test_deployment_config.py` prod↔settings eşitliğini zorlar).
- `src/domain/*` adapters/application import etmez. Merge yok; dal `feat/s2-freshness-ingest-portfolio` (S1 üzerine kurulu).

## Review Focus

- Feed'in `pubDate`'i olmayan / bozuk / tz'siz (naive) öğeleri → çökme yok, elenmeden sona düşer (Task 1 testi).
- Tarih sırasız feed'de (ScienceDaily 60 öğe) en taze 25 seçilmeli, feed başındaki 25 değil (Task 4 testi).
- Günlük bütçe 0 veya negatif (dolu) → hiçbir haber analiz edilmez, Groq çağrısı YOK (Task 3 testi).
- `SOURCE_DAILY_CAPS` bozuk JSON / sayı olmayan değer → uyarı loglanır, varsayılan tavanlara düşülür, uygulama açılır (Task 2 testi).
- Kaynak eklenip prod compose'a unutulması (10 Eylül dersi) → `test_deployment_config` kırmızı (Task 5).

## File Structure

| Dosya | Sorumluluk |
|---|---|
| Create `src/domain/policies/__init__.py`, `src/domain/policies/ingest_policy.py` | `sort_newest_first`, `select_for_analysis` (saf) |
| Create `src/adapters/scrapers/source_policy.py` | `parse_cap_overrides`, `effective_daily_cap` |
| Modify `src/adapters/scrapers/rss_scrapers.py` | Base: `language/focus_topic/daily_cap`, parse→sort→slice; 11 yeni sınıf; mevcut sınıflara meta veri |
| Modify `src/adapters/scrapers/registry.py`, `src/domain/scoring/credibility.py` | kayıtlar |
| Modify `src/domain/ports/news_repository_port.py`, `src/adapters/repositories/news_repository.py` | `count_articles_since` |
| Modify `src/application/services/news_service.py` | politika kullanımı, `daily_cap` parametresi |
| Modify `src/adapters/messaging/kafka_consumer.py` | tavanı çözüp servise verir |
| Modify `src/adapters/api/metrics.py` | `source_capped_total`; `articles_processed_total` `topic` etiketi |
| Modify `src/infrastructure/config/settings.py`, `docker-compose.yml`, `docker-compose.prod.yml` | `max_article_age_hours`, `source_daily_caps`, `scrape_sources` |
| Tests | `tests/domain/test_ingest_policy.py`, `tests/adapters/test_source_policy.py`, `tests/adapters/test_source_portfolio.py`, eklemeler mevcut dosyalara |

---

### Task 1: Alım politikası (saf domain)
**Files:** Create `src/domain/policies/{__init__,ingest_policy}.py`; Test `tests/domain/test_ingest_policy.py`
**Interfaces — Produces:** `sort_newest_first(articles) -> List[Article]` (kararlı; tarihsizler sonda; naive tarih UTC sayılır); `select_for_analysis(articles, *, now: datetime, max_age_hours: int, daily_budget_left: Optional[int], per_run_limit: Optional[int]) -> List[Article]`.

- [ ] Test (önce): yaş süzgeci (49 sa eski elenir, 47 sa kalır), taze→eski sıra, tarihsiz sonda ve elenmez, naive tarih çökmez, `daily_budget_left=0` ve `-3` → `[]`, `per_run_limit=2` kesmesi, `None` sınırsız, bütçe ve limitten küçük olan kazanır.
- [ ] RED çalıştır → modül yok.
- [ ] Uygula: `_aware(dt)` (naive→UTC), `_key(a)` = `(a.published_at is None, -timestamp)`; `select_for_analysis` = süz → sırala → `min` sınırlar.
- [ ] GREEN + commit `feat(ingest): tazelik oncelikli secim politikasi`.

### Task 2: Kaynak profili ve tavan çözümleme
**Files:** Create `src/adapters/scrapers/source_policy.py`; Modify `settings.py` (`max_article_age_hours: int = 48`, `source_daily_caps: str = ""`); Test `tests/adapters/test_source_policy.py`
**Interfaces — Produces:** `parse_cap_overrides(raw: str) -> Dict[str, int]` (bozuk JSON/değer → `{}` + uyarı; negatif/0 → yok sayılır); `effective_daily_cap(source_name: str, default: Optional[int], overrides: Dict[str,int]) -> Optional[int]`.

- [ ] Test: geçerli JSON, boş string, bozuk JSON, `{"CNN Türk": "x"}` (sayı değil → atlanır, diğerleri kalır), `effective_daily_cap` override > default > `None`.
- [ ] RED → uygula (`json.loads`, `int()`, try/except, `logger.warning`) → GREEN → commit.

### Task 3: Repository `count_articles_since` + servis entegrasyonu
**Files:** Modify port/repo (`count_articles_since(source: str, since: datetime) -> int`), `news_service.py::update_news_from_source(..., daily_cap: Optional[int] = None)`, `metrics.py`, `kafka_consumer.py`; Test `tests/adapters/test_news_repository.py`, `tests/application/test_news_service.py`
**Interfaces — Consumes:** Task 1 `select_for_analysis`, Task 2 `effective_daily_cap`/`parse_cap_overrides`. **Produces:** metrik `source_capped_total` (Counter, `source`), `articles_processed_total` etiketleri `(source, status, topic)`.

- [ ] Repo testi (sqlite in-memory): 3 kayıt (2 taze 1 eski) → sayı 2; başka kaynak sayılmaz.
- [ ] Servis testleri: (a) `daily_cap=2`, 1 zaten bugün kayıtlı, 5 yeni → analyzer 1 kez çağrılır; (b) bütçe dolu → analyzer HİÇ çağrılmaz + `source_capped_total` artar; (c) 60 saat eski haber atlanır; (d) en taze haber önce analiz edilir (çağrı sırası); (e) `daily_cap=None` eski davranış.
- [ ] RED → uygula: `articles` boşsa erken dön; `source = articles[0].source`; `left = None if daily_cap is None else daily_cap - repo.count_articles_since(source, now-24h)`; `new_articles = select_for_analysis(new_articles, now=..., max_age_hours=settings.max_article_age_hours, daily_budget_left=left, per_run_limit=max_new_articles)`; bütçe ≤ 0 iken `source_capped_total.labels(source).inc()`.
- [ ] `kafka_consumer`: `overrides = parse_cap_overrides(settings.source_daily_caps)`; `cap = effective_daily_cap(scraper.source_name, getattr(scraper, "daily_cap", None), overrides)`; `update_news_from_source(scraper, max_new_articles=..., daily_cap=cap)`.
- [ ] Metrik: `articles_processed_total.labels(source=..., status="saved", topic=article.topic or "Other")`; mevcut çağrı yerleri ve testler güncellenir.
- [ ] Tam paket GREEN + commit.

### Task 4: Scraper tabanı — önce ayrıştır, sırala, sonra dilimle
**Files:** Modify `rss_scrapers.py::BaseRssScraper` (+ sınıf öznitelikleri `language = "TR"`, `focus_topic: Optional[str] = None`, `daily_cap: Optional[int] = None`); Test `tests/adapters/test_rss_scrapers.py`
- [ ] Test: 30 öğeli feed, EN ESKİ ilk sırada, en yeniler sonda, `limit=5` → dönen 5 haber EN YENİ 5'tir ve yeniden eskiye sıralı; `pubDate`'siz öğe sona düşer.
- [ ] RED → uygula: tüm öğeleri `Article`'a çevir → `sort_newest_first` → `[:limit]`.
- [ ] Tam paket + commit.

### Task 5: 11 yeni kaynak, meta veri, kapasite testi
**Files:** Modify `rss_scrapers.py` (11 yeni sınıf + mevcut 17'ye `language/focus_topic/daily_cap`), `registry.py`, `credibility.py`, `settings.scrape_sources`, `docker-compose.yml`, `docker-compose.prod.yml`; Test `tests/adapters/test_source_portfolio.py`, `tests/adapters/test_rss_scrapers.py` (parametrik liste), `tests/infrastructure/test_settings.py`
**Yeni kaynaklar (URL'ler 29 Eyl'de canlı doğrulandı; Cointelegraph prod IP'den):** Dünya `https://www.dunya.com/rss` (TR, Economy, cap 50, 0.70) · CoinDesk `https://www.coindesk.com/arc/outboundfeeds/rss/` (EN, Crypto, 25, 0.70) · Cointelegraph `https://cointelegraph.com/rss` (EN, Crypto, 25, 0.65) · ScienceDaily `https://www.sciencedaily.com/rss/all.xml` (EN, Science, 15, 0.75) · AA Bilim-Teknoloji `https://www.aa.com.tr/tr/rss/default?cat=bilim-teknoloji` (TR, Science, 25, 0.75) · AA Kültür `…?cat=kultur` (TR, Culture, 20, 0.75) · Al Jazeera `https://www.aljazeera.com/xml/rss/all.xml` (EN, World, 40, 0.75) · DW `https://rss.dw.com/xml/rss-en-all` (EN, World, 30, 0.80) · BBC Health `https://feeds.bbci.co.uk/news/health/rss.xml` (EN, Health, 15, 0.90) · BBC Entertainment `https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml` (EN, Entertainment, 15, 0.85) · BBC Science & Environment `https://feeds.bbci.co.uk/news/science_and_environment/rss.xml` (EN, Environment, 10, 0.90).
**Mevcut kaynak tavanları (24 sa ölçümüne göre):** CNN Türk 120, Sözcü 100, Anadolu Ajansı 100, TRT Haber 100, Habertürk 80, Hürriyet 70, Sabah 60, BBC Türkçe 30, HT Spor 60, Hürriyet Spor 50, BBC Sport 60, AA Ekonomi 25, Hacker News 60, TechCrunch 30, The Verge 30, Guardian Tech 20, BBC Technology 10. **Toplam ≤ 950.**
- [ ] `test_source_portfolio.py` (önce): her kayıtlı scraper'ın `focus_topic ∈ {None} ∪ VALID_TOPIC_IDS`, `language ∈ {TR, EN}`, `daily_cap` int>0; Politics/Other hariç her konunun ≥1 odaklı kaynağı var; `sum(daily_cap) <= 950`; her kaynağın `credibility` tablosunda satırı var; her kaynak `settings.scrape_sources` içinde.
- [ ] RED → sınıfları/kayıtları yaz → GREEN; `test_deployment_config` (prod/dev compose ↔ settings) GREEN.
- [ ] Tam paket + commit.

### Task 6: Belgeler, doğrulama, PR
- [ ] CLAUDE.md: "Yeni kaynak kontrol listesi" güncellemesi (scraper+meta veri, registry, credibility, settings, 2 compose, tavan toplamı testi) + tazelik-öncelikli alım kuralı. CHANGELOG girişi (canlı feed doğrulama tablosu, tavanlar, kapasite modeli, deploy sonrası izlenecekler: `nexstream_source_capped_total`, konu dağılımı, nötr-yedek oranı ≤ %5, yeni kaynakların ilk saatleri).
- [ ] Tam paket, `git push`, `gh pr create` (merge YOK).

## Self-Review
Spec §4.2: tazelik sırası + yaş süzgeci ✓ (T1,T3), tavan + metrik ✓ (T2,T3), kaynak meta verisi ✓ (T4,T5), topic metriği ✓ (T3), portföy ✓ (T5), deployment_config ✓ (T5). §5 kapasite modeli testle kilitli ✓. Sapmalar: yok. Not: sıra-bağımsız feed'ler için sıralama scraper'da (T4) VE politikada (T1) yapılır — T4 dilimlemeden ÖNCE, T1 alım kararında; aynı `sort_newest_first` yardımcısı (tek uygulama).
