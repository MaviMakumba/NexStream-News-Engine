# NexStream News Engine — CLAUDE.md

Bu dosya Claude Code için proje bağlamını sağlar.
Her session başında oku, sonra gerekli dosyaları kendin aç.

---

## MİMARİ

Hexagonal (Ports & Adapters) mimari. Domain katmanı hiçbir dış bağımlılık bilmez.
Bağımlılık yönü: Adapter → Application → Domain. Tersi yasak.

```
src/
├── domain/
│   ├── models/article.py          # Article dataclass — merkezi model
│   ├── ports/
│   │   ├── analysis_port.py       # class AnalysisPort (ABC)
│   │   ├── news_scraper_port.py   # class NewsScraperPort (ABC)
│   │   ├── news_repository_port.py
│   │   ├── messaging_port.py      # class MessagePublisherPort (ABC)
│   │   └── embedding_port.py      # class EmbeddingPort (ABC)
│   └── schemas/
│       └── news_schema.py         # Pydantic: NewsResponse, SearchRequest, SearchResult
├── application/
│   └── services/news_service.py   # Orchestration — port'ları bağlar, reindex_all dahil
├── adapters/
│   ├── analysis/
│   │   └── groq_analyzer.py       # Groq llama-3.3-70b-versatile
│   ├── scrapers/
│   │   └── rss_scrapers.py        # BBC Tech/Sport, TRT, BBC Türkçe, Hürriyet, Hürriyet Spor
│   ├── repositories/
│   │   ├── news_orm.py            # SQLAlchemy ORM modeli
│   │   └── news_repository.py     # PostgreSQL adapter
│   ├── messaging/
│   │   ├── kafka_consumer.py      # Worker: consume → scrape → analyze → save → index
│   │   └── kafka_publisher.py
│   ├── scheduling/
│   │   └── scheduler_service.py   # 10dk'da bir Kafka'ya mesaj atar
│   ├── search/
│   │   ├── sentence_transformer_embedder.py  # SentenceTransformerEmbedder (singleton)
│   │   └── chroma_search_repository.py       # ChromaDB adapter — index + search
│   └── api/
│       └── routers/news_router.py  # GET /news, POST /scrape, /search, /reindex
├── infrastructure/
│   └── config/database.py        # SQLAlchemy engine — ayrı DB_* env var kullanır
├── dependencies.py                # FastAPI DI — GroqAnalyzer, NewsRepository, ChromaSearch inject
└── main.py                        # FastAPI app
dashboard/
└── app.py                         # Streamlit — API_BASE=http://app:8000, semantik arama dahil
tests/
├── domain/test_article.py
├── application/test_news_service.py
├── adapters/test_rss_scrapers.py
├── adapters/test_news_repository.py
├── adapters/test_groq_analyzer.py
└── adapters/test_chroma_search_repository.py
```

---

## DOCKER SERVİSLER (docker-compose.yml)

| Servis | Port | Açıklama |
|--------|------|----------|
| app | 8000 | FastAPI |
| db | 5432 (env) | PostgreSQL 15 |
| adminer | 8080 | DB yönetim UI |
| zookeeper | 2181 | Kafka koordinatör |
| kafka | 9092 | Mesaj kuyruğu |
| worker | — | Kafka consumer + Groq analyzer |
| scheduler | — | 10dk'da bir scrape tetikler |
| dashboard | 8501 | Streamlit |
| chromadb | 8001 (host) / 8000 (container) | Vektör DB |

Container içi Chroma bağlantısı: `http://chromadb:8000`
Env var: `CHROMA_HOST=chromadb`, `CHROMA_PORT=8000`

---

## KRİTİK KARARLAR VE GEREKÇELERİ

**Neden Groq?** Gemini'den taşındı. 14.400 req/gün ücretsiz, llama-3.3-70b TR+EN destekler, requests kütüphanesi yeterli (SDK yok).

**Neden sentence-transformers?** Groq'un embedding API'si yok. `paraphrase-multilingual-MiniLM-L12-v2` modeli TR+EN destekler, tamamen local çalışır, API key gerektirmez. Kurulu versiyon: 3.3.1, torch: 2.10.0, chromadb: 1.5.5

**Neden ChromaDB?** Local, ücretsiz, Docker'a kolay eklenir, persistent storage destekler. `IS_PERSISTENT=TRUE` env var ile volume'a yazar.

**Neden hexagonal?** Kurs projesi — kurumsal mimari dersi için. Separation of concerns önemli. Yeni adapter eklemek domain'i bozmaz.

**Database URL:** `DATABASE_URL` env var yok. Ayrı `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` kullanılır. `src/infrastructure/config/database.py`'a bak.

**TextBlob:** Tamamen kaldırıldı. Groq ile değiştirildi. Hiçbir yerde TextBlob kullanma.

---

## MEVCUT DURUM

- **Test sayısı:** 73 test, hepsi yeşil
- **CI/CD:** GitHub Actions — push/PR on main, postgres:15 service, `python -m pytest`
- **Branch:** main (tüm özellikler merge edildi)
- **Versiyon:** v1.2.0-dev — Hybrid Search tamamlandı

---

## SIRADAKI GÖREV: v1.2.0 (devam)

### ✅ Tamamlanan — Hybrid Search
- `POST /news/search` artık ChromaDB (semantic) + PostgreSQL (keyword) birleşik çalışıyor
- Query tokenize ediliyor; her kelime ayrı ILIKE ile aranıyor
- Coverage-based skor: başlık×0.9, özet×0.7, içerik×0.5
- Birleşik skor: `max(sem, kw) + 0.10 bonus` (her ikisinde varsa)
- Aday havuzu: `max(n_results×3, 20)` — sıralama daha geniş kümeden yapılıyor
- Normalize edilmiş embedding (`normalize_embeddings=True`) + `1/(1+distance)` formülü

**⚠️ Deploy sonrası yapılacak:**
```powershell
docker-compose up --build   # embedder kodu değişti
# Sonra: POST /news/reindex  # ChromaDB'yi normalize edilmiş vektörlerle yeniden index et
```

### Öncelik 2 — Yeni Haber Kaynakları
- Sabah, CNN Türk RSS feed'leri
- Reuters / AP (EN)
- NTV: RSS yok, alternatif kaynak araştır

### Öncelik 3 — Dashboard Geliştirmeleri
- Arama geçmişi (session state)
- Detay sayfası: URL açma, tam içerik gösterme
- Kaynak bazlı sentiment karşılaştırma grafiği

### Öncelik 4 — Gözlemlenebilirlik
- `GET /health` endpoint: DB + Kafka + ChromaDB durumu
- ChromaDB index sayısı dashboard'da görünür
- Worker log'larını dashboard'dan izleme

---

## KODLAMA KURALLARI

- Port isimleri: `*Port` (AnalysisPort, EmbeddingPort)
- Adapter isimleri: açıklayıcı (`GroqAnalyzer`, `SentenceTransformerEmbedder`)
- Import sırası: stdlib → third party → local (src.*)
- Tüm env var'lar `os.getenv()` ile, default değer ver
- Exception'ları yut, logla, fallback dön — servis çökmemeli
- Test'lerde gerçek API çağrısı yok, her şey mock

---

## ÇALIŞMA KOMUTLARI

```powershell
# Test
venv\Scripts\python.exe -m pytest tests/ -v

# Belirli test dosyası
venv\Scripts\python.exe -m pytest tests/adapters/test_groq_analyzer.py -v

# Docker — kod değiştiyse
docker-compose restart worker
docker-compose restart app

# Docker — requirements değiştiyse
docker-compose up --build

# Docker — sıfırdan (DB + ChromaDB silinir)
docker-compose down -v && docker-compose up --build

# Loglar
docker logs nexstream_worker --tail 30
docker logs nexstream_chromadb --tail 20
```

---

## BİLİNEN NOTLAR

- Groq free tier: 14.400 req/gün — production'da dikkat
- Scraper limit: 25 haber/kaynak/çalışma
- DB duplicate kontrolü var — aynı URL tekrar kaydedilmez
- NTV scrapers çalışmıyor (HTML dönüyor, RSS yok) — ekleme
- ChromaDB 1.5.5 kurulu (0.5.23 uvicorn conflict veriyordu)
- `docker-compose down -v` sonrası ChromaDB da sıfırlanır
- Dashboard sidebar kaldırıldı, tüm kontroller üst bar'da
- README'deki YOUR_USERNAME henüz değiştirilmedi
