<div align="center">

# NexStream News Engine

**AI-Powered Multi-Source News Intelligence Platform**

[![Tests](https://github.com/MaviMakumba/NexStream-News-Engine/actions/workflows/tests.yml/badge.svg)](https://github.com/MaviMakumba/NexStream-News-Engine/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.129-009688?logo=fastapi)
![Kafka](https://img.shields.io/badge/Apache_Kafka-2.8-231F20?logo=apachekafka)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-green)

[English](#english) · [Türkçe](#turkce)

</div>

---

<a name="english"></a>
## English

### Overview

NexStream is an event-driven news aggregation and intelligence platform. It continuously collects articles from 11 sources in English and Turkish, processes them through an AI pipeline (sentiment analysis, summarization), enables hybrid semantic + keyword search, and presents insights through an interactive real-time dashboard.

**Key capabilities:**
- Collects news from **11 sources** in English and Turkish
- Analyzes sentiment and generates summaries using Groq's `llama-3.1-8b-instant` model
- Performs **hybrid search**: ChromaDB semantic vectors + PostgreSQL full-text, ranked by a combined score
- Streams events through Apache Kafka for decoupled, resilient processing
- Real-time health monitoring: DB, Kafka, and ChromaDB status visible in the dashboard
- Fully containerized with Docker Compose — one command to start everything
- **97 tests**, all green, CI via GitHub Actions

---

### Architecture

NexStream is built on **Hexagonal Architecture (Ports & Adapters)**. The domain layer has zero knowledge of external systems; adapters implement ports and are wired together in `dependencies.py`.

```
+----------------------------------------------------------+
|                      DOMAIN LAYER                        |
|         Article Model + Ports (Interfaces/ABCs)          |
+----------------------------------------------------------+
                            |
+----------------------------------------------------------+
|                   APPLICATION LAYER                      |
|                      NewsService                         |
+----------------------------------------------------------+
                            |
+----------------------------------------------------------+
|                    ADAPTERS LAYER                        |
|                                                          |
|  Scrapers          Analyzer         Repository    API    |
|  ---------         --------         ----------   -----  |
|  11 RSS feeds      Groq LLM         PostgreSQL   FastAPI |
|  (TR + EN)         llama-3.1-8b     SQLAlchemy   REST    |
|                                                          |
|  Messaging         Scheduling       Vector Search        |
|  ---------         ----------       -------------        |
|  Apache Kafka      APScheduler      ChromaDB             |
|  (producer +       (10-min          sentence-            |
|   consumer)         trigger)        transformers         |
+----------------------------------------------------------+
```

**Event Flow:**

```
Scheduler (10 min)
        |
        v
FastAPI /news/scrape  ------>  Kafka Topic: news_updates
                                        |
                                        v
                               Kafka Worker (consumer)
                                        |
                          +-------------+
                          |  RSS Scraper         |
                          |  (fetch 11 sources)  |
                          +---------------------+
                                        |
                          +-------------+
                          |  Groq Analyzer       |
                          |  (sentiment + summary)|
                          +---------------------+
                                        |
                          +-------------+
                          |  PostgreSQL          |
                          |  (persist article)   |
                          +---------------------+
                                        |
                          +-------------+
                          |  ChromaDB            |
                          |  (index embedding)   |
                          +---------------------+
                                        |
                          +-------------+
                          |  Next.js Frontend    |
                          |  (cinematic UI)      |
                          +---------------------+
```

---

### Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| Message Broker | Apache Kafka + Zookeeper |
| AI Analyzer | Groq API — `llama-3.1-8b-instant` |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (local, no API key) |
| Vector Search | ChromaDB 1.5.5 (persistent, Docker) |
| Database | PostgreSQL 15 + SQLAlchemy ORM |
| Frontend | Next.js 14 + React — 9 cinematic themes (CSS + Canvas) |
| Scheduler | APScheduler |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Testing | pytest (343 tests) |

---

### News Sources (11)

| Source | Language | Category |
|--------|----------|----------|
| BBC Technology | English | Technology |
| BBC Sport | English | Sports |
| TRT Haber | Turkish | General |
| BBC Türkçe | Turkish | General |
| Hürriyet | Turkish | General |
| Hürriyet Spor | Turkish | Sports |
| Sabah | Turkish | General |
| CNN Türk | Turkish | General |
| Sözcü | Turkish | General |
| Habertürk | Turkish | General |
| HT Spor | Turkish | Sports |

New sources can be added in 6 lines — see [Adding a News Source](#adding-a-news-source).

---

### Frontend (Next.js)

The original Streamlit dashboard was replaced by a **Next.js 14 + React** frontend with a distinctive **cinematic theme system**:

- **9 cinematic themes** — Matrix, Godfather, Blade Runner, Dune, Star Wars, Spider-Man, Batman, Wolfenstein + a clean **Day** mode. Each theme transforms colors, fonts, an animated full-screen **Canvas background** (digital rain, film grain, neon rain, sandstorm, starfield, web mesh, bat-signal, embers) and plays a transition flash on switch. **Pure CSS + Canvas — no images or video assets.**
- **Theme registry** (`lib/theme/registry.ts`): single source of truth. Add a theme = one registry entry + one CSS block + one effect, with zero consumer changes (Open/Closed).
- **Full TR / EN i18n**: every string localized — landing, dashboard, account, and admin pages all switch language together.
- **Trending pills** (clickable → semantic search), hybrid semantic search, related-article graph, user accounts, tiered API, Stripe billing, and an admin panel.
- Honors `prefers-reduced-motion` and pauses animations when the browser tab is hidden (single shared `requestAnimationFrame` loop).

---

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/news/` | List articles (filter by source, sentiment) |
| POST | `/news/scrape` | Trigger scrape for a source |
| POST | `/news/search` | Hybrid semantic + keyword search |
| POST | `/news/reindex` | Rebuild ChromaDB index from DB |
| GET | `/news/sources` | List all registered sources |
| GET | `/health` | System health: DB + Kafka + ChromaDB + vector count |
| GET | `/docs` | Swagger UI |

---

### Getting Started

#### Prerequisites
- Docker Desktop
- Git
- Groq API Key (free at [console.groq.com](https://console.groq.com))

#### Installation

```bash
# 1. Clone the repository
git clone https://github.com/MaviMakumba/NexStream-News-Engine.git
cd NexStream-News-Engine

# 2. Create environment file
cp .env.example .env

# 3. Add your Groq API key to .env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# 4. Start all services
docker-compose up --build
```

#### Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Next.js UI |
| API | http://localhost:8000 | FastAPI REST |
| API Docs | http://localhost:8000/docs | Swagger UI |
| DB Admin | http://localhost:8080 | Adminer |

#### First Run

Once all containers are healthy, open the frontend at `http://localhost:3000`. The scheduler automatically triggers scraping every 10 minutes and the Kafka worker processes articles through the AI analyzer — no manual action needed. Check `http://localhost:8000/health` to confirm DB, Kafka, and ChromaDB are all green.

---

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run a specific file
python -m pytest tests/adapters/test_rss_scrapers.py -v
```

**Test coverage: 97 tests across 6 modules**

---

### Adding a News Source

Thanks to the `BaseRssScraper` pattern and the source registry, adding a new source takes only a few lines:

```python
# src/adapters/scrapers/rss_scrapers.py
class MyNewsScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://example.com/rss"
        self.source_name = "My News"
        self.limit = 25
```

Then register it in `src/adapters/scrapers/registry.py`:

```python
SCRAPER_REGISTRY = {
    ...
    "My News": MyNewsScraper(),
}
```

---

### Adding a New AI Analyzer

Implement the `AnalysisPort` interface and swap it in `dependencies.py` — zero changes to business logic:

```python
# src/adapters/analysis/my_analyzer.py
class MyAnalyzer(AnalysisPort):
    def analyze_text(self, text: str) -> dict:
        return {
            "sentiment_score": 0.8,
            "sentiment_label": "Positive",
            "summary": "..."
        }
```

---

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key | `gsk_xxx...` |
| `DB_HOST` | PostgreSQL host | `db` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `nexstream_db` |
| `DB_USER` | Database user | `nexstream` |
| `DB_PASSWORD` | Database password | `nexstream` |
| `CHROMA_HOST` | ChromaDB host | `chromadb` |
| `CHROMA_PORT` | ChromaDB port (container) | `8000` |

---

### CI/CD

Every push to `main` triggers the GitHub Actions pipeline:

1. Spins up a PostgreSQL 15 service container
2. Installs Python dependencies
3. Runs all 97 tests with `pytest`
4. Reports pass/fail status

---

### Roadmap

| Milestone | Focus | Status |
|-----------|-------|--------|
| v1.2.0 | Hybrid search, 11 sources, dashboard overhaul, health endpoint | Done |
| v1.3.0 | Foundation hardening: Pydantic Settings, structured logging, API auth, rate limiting, network isolation | Next |
| v1.4.0 | Performance: async scraping, batch processing, pub_date, PostgreSQL indexes | Planned |
| v1.5.0 | AI features: NER, topic classification, trending engine, semantic dedup | Planned |
| v1.6.0 | Production deployment: Nginx + HTTPS, Prometheus + Grafana, backup automation | Planned |

v1.6 target: production-deployable on a single VPS (DigitalOcean / Hetzner / Oracle Free Tier).

---

### License

MIT License — see [LICENSE](LICENSE) for details.

---

<a name="turkce"></a>
## Türkçe

### Genel Bakış

NexStream, 11 kaynaktan Türkçe ve İngilizce haber toplayıp yapay zeka ile analiz eden ve sonuçları interaktif bir panelde sunan olay güdümlü bir haber platformudur. Dil modeli sayesinde her habere duygu analizi ve özet eklenir; hibrit arama sayesinde hem anlamsal (ChromaDB) hem anahtar kelime (PostgreSQL) eşleştirmesi yapılır.

**Temel özellikler:**
- **11 kaynaktan** Türkçe ve İngilizce haber toplar
- Groq `llama-3.1-8b-instant` ile duygu analizi ve özetleme yapar
- **Hibrit arama**: ChromaDB anlam vektörü + PostgreSQL tam metin, birleşik skor
- Apache Kafka ile servisler arası bağımsız, dayanıklı veri akışı
- Dashboard'da gerçek zamanlı sağlık göstergesi (DB / Kafka / ChromaDB)
- Docker Compose ile tek komutla başlatılır
- **97 test**, hepsi yeşil; GitHub Actions CI

---

### Mimari

NexStream, **Hexagonal Mimari (Ports & Adapters)** üzerine inşa edilmiştir. Domain katmanı dış sistemleri tanımaz; adapter'lar port'ları implemente eder, `dependencies.py` bunları birbirine bağlar.

```
Zamanlayıcı (10dk)
        |
        v
FastAPI /news/scrape  ------>  Kafka: news_updates
                                        |
                                        v
                               Kafka Worker
                                        |
                          +---------------------------+
                          |  RSS Scraper              |
                          |  (11 TR+EN kaynak)        |
                          +---------------------------+
                                        |
                          +---------------------------+
                          |  Groq Analyzer            |
                          |  (duygu + özet)           |
                          +---------------------------+
                                        |
                          +---------------------------+
                          |  PostgreSQL               |
                          |  (kaydet)                 |
                          +---------------------------+
                                        |
                          +---------------------------+
                          |  ChromaDB                 |
                          |  (vektör indexle)         |
                          +---------------------------+
                                        |
                          +---------------------------+
                          |  Next.js Frontend         |
                          |  (sinematik arayüz)       |
                          +---------------------------+
```

---

### Hızlı Başlangıç

```bash
# 1. Repoyu klonla
git clone https://github.com/MaviMakumba/NexStream-News-Engine.git
cd NexStream-News-Engine

# 2. Ortam dosyasını oluştur
cp .env.example .env

# 3. .env dosyasına Groq API anahtarını ekle
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# 4. Tüm servisleri başlat
docker-compose up --build
```

Konteynerler ayağa kalktıktan sonra `http://localhost:3000` adresindeki arayüzü aç. Scheduler her 10 dakikada bir scrape'i otomatik tetikler ve Kafka worker haberleri AI analizinden geçirir — manuel işlem gerekmez. `http://localhost:8000/health` ile DB / Kafka / ChromaDB'nin yeşil olduğunu doğrulayabilirsin.

---

### Testleri Çalıştırma

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

---

### Haber Kaynakları (11)

| Kaynak | Dil | Kategori |
|--------|-----|---------|
| BBC Technology | İngilizce | Teknoloji |
| BBC Sport | İngilizce | Spor |
| TRT Haber | Türkçe | Genel |
| BBC Türkçe | Türkçe | Genel |
| Hürriyet | Türkçe | Genel |
| Hürriyet Spor | Türkçe | Spor |
| Sabah | Türkçe | Genel |
| CNN Türk | Türkçe | Genel |
| Sözcü | Türkçe | Genel |
| Habertürk | Türkçe | Genel |
| HT Spor | Türkçe | Spor |

---

### Katkıda Bulunma

1. Repoyu fork'la
2. Feature branch oluştur: `git checkout -b feat/yeni-ozellik`
3. Değişikliklerini commit'le: `git commit -m "feat: yeni özellik ekle"`
4. Branch'ini push'la: `git push origin feat/yeni-ozellik`
5. Pull Request aç

Commit mesajları için [Conventional Commits](https://www.conventionalcommits.org/) standardı kullanılmaktadır.

| Prefix | Kullanım |
|--------|----------|
| `feat:` | Yeni özellik |
| `fix:` | Hata düzeltme |
| `chore:` | Bakım, temizlik |
| `ci:` | CI/CD değişikliği |
| `refactor:` | Kod iyileştirme |
| `test:` | Test ekleme/güncelleme |
| `docs:` | Dokümantasyon |

---

### Yol Haritası

| Milestone | Odak | Durum |
|-----------|------|-------|
| v1.2.0 | Hibrit arama, 11 kaynak, dashboard overhaul, health endpoint | Tamamlandı |
| v1.3.0 | Temel sertleştirme: Pydantic Settings, structured logging, API auth, rate limiting | Sıradaki |
| v1.4.0 | Performans: async scraping, batch processing, pub_date, PostgreSQL index'leri | Planlandı |
| v1.5.0 | AI özellikleri: NER, konu sınıflandırma, trending engine, semantik dedup | Planlandı |
| v1.6.0 | Production deploy: Nginx + HTTPS, Prometheus + Grafana, backup otomasyonu | Planlandı |

v1.6 hedefi: tek VPS'e (DigitalOcean / Hetzner / Oracle Free Tier) production deploy edilebilir hale gelmek.

---

<div align="center">

**NexStream** · Built with Python, FastAPI, Kafka, and Groq

</div>
