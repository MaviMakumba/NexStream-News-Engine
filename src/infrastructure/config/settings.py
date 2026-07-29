"""Merkezi uygulama yapılandırması (Pydantic Settings).

Tüm ortam değişkenleri TEK noktadan okunur — `os.getenv()` kullanımı yasaktır.
Değerler `.env` dosyasından veya ortam değişkenlerinden gelir; alan adları
büyük/küçük harf duyarsız eşleşir (örn. `DB_HOST` → `db_host`).

Kullanım:
    from src.infrastructure.config.settings import settings
    settings.groq_api_key
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Prod deploy'da docker-compose.prod.yml ENVIRONMENT=production set eder —
    # dev'de varsayılan "development" kalır, aşağıdaki güvenlik guard'ı devre dışı.
    environment: str = "development"

    # ── Database (PostgreSQL) ──────────────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "nexstream"
    db_password: str = "nexstream"
    db_name: str = "nexstream_db"

    # ── LLM analiz (Groq birincil, HuggingFace opsiyonel yedek) ────────────
    groq_api_key: str = ""
    huggingface_api_key: str = ""    # boşsa fallback zinciri devre dışı kalır
    huggingface_model: str = "mistralai/Mistral-7B-Instruct-v0.3"

    # ── ChromaDB (vektör arama) ────────────────────────────────────────────
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # ── Embedder servisi (v2.0 RAM optimizasyonu) ──────────────────────────
    # Model app/worker içinde DEĞİL, ayrı bir serviste tek kopya durur.
    # "local" mod modeli süreç içine yükler — yalnızca Docker'sız geliştirme için.
    embedder_mode: str = "http"                    # "http" | "local"
    embedder_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedder_url: str = "http://embedder:8000"
    embedder_connect_timeout: float = 2.0          # aynı Docker ağı; aşılıyorsa servis yok
    embedder_read_timeout: float = 5.0             # tek embedding CPU'da ~10-30ms
    embedder_batch_read_timeout: float = 30.0      # toplu indeksleme partileri
    embedder_retries: int = 1                      # toplam 2 deneme — asılı servis
                                                   # worker döngüsünü uzun bloklamamalı

    # ── Kafka-uyumlu mesajlaşma (Redpanda broker, v1.18'de Kafka+Zookeeper'ın
    # yerine geçti — arm64 destek için, bkz. DEPLOY.md). Alan adları wire-
    # protokolü tanımlıyor, broker yazılımını değil; bu yüzden korundu.
    kafka_bootstrap_servers: str = "redpanda:29092"
    kafka_host: str = "redpanda"
    kafka_port: int = 29092

    # ── Scheduler — taranacak kaynaklar (registry isimleriyle eşleşmeli) ───
    scrape_sources: str = (
        "TRT Haber,BBC Türkçe,Hürriyet,Hürriyet Spor,Sabah,"
        "CNN Türk,Sözcü,Habertürk,HT Spor,Anadolu Ajansı,AA Ekonomi,"
        "BBC Technology,BBC Sport,Guardian Tech,TechCrunch,Hacker News,The Verge"
    )

    # ── API güvenliği ──────────────────────────────────────────────────────
    # Paylaşımlı makine-makine anahtarı (X-API-Key). İnsan kullanıcılar için
    # v1.13'ten itibaren rol tabanlı yetki (users.role) tercih edilir.
    api_key: str = "dev-key-change-me"
    # Virgülle ayrılmış e-posta listesi; eşleşen kullanıcılar otomatik admin
    # sayılır (DB'ye yazmadan, okuma anında). Örn: "ben@mail.com,sen@mail.com"
    admin_emails: str = ""

    # ── Logging ────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "json"            # "json" | "text"

    # ── CORS ───────────────────────────────────────────────────────────────
    cors_origins: str = "*"             # virgülle ayrılmış origin listesi

    # ── Email (newsletter / keyword alert) ─────────────────────────────────
    resend_api_key: str = ""            # boşsa console adapter (sadece log)
    email_from: str = "NexStream <no-reply@nexstream.news>"
    newsletter_hour_utc: int = 6        # günlük digest saati (06:00 UTC = 09:00 TR)

    # ── Auth / Sessions ────────────────────────────────────────────────────
    session_ttl_days: int = 30
    # Oturum cookie'sinin Secure bayrağı — prod'da HTTPS üzerinden True olmalı;
    # dev'de HTTP olduğu için False (Secure cookie HTTP'de hiç gönderilmez).
    session_cookie_secure: bool = True
    # Şifre sıfırlama linkinin hedeflediği frontend origin'i (mail içindeki link).
    frontend_url: str = "http://localhost:3000"
    password_reset_ttl_minutes: int = 60
    # E-posta doğrulama linkinin geçerlilik süresi (v1.15) — şifre sıfırlamadan
    # daha uzun: kullanıcı kayıttan hemen sonra tıklamak zorunda değil (yumuşak
    # gating, Free tier zaten tam erişimli).
    email_verification_ttl_minutes: int = 1440
    # Backend API'nin dışarıdan erişilebilir kök adresi — mail içindeki "aboneliği
    # iptal et" linki gibi doğrudan API'ye giden bağlantılar için. Prod'da nginx
    # /api/ altında proxy'lediği için gerçek domain + /api olmalı (örn. https://nexstream.news/api).
    api_base_url: str = "http://localhost:8000"

    # ── Billing (Stripe) ───────────────────────────────────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_enterprise_price_id: str = ""
    # v1.11: Stripe yapılandırılmadan lokal demo için tier yükseltme simülasyonu.
    # True iken /billing/checkout ödeme almadan tier'ı anında günceller.
    # PRODUCTION'DA ASLA AÇILMAMALIDIR.
    billing_dev_mode: bool = False

    # ── Redis (cache) ──────────────────────────────────────────────────────
    redis_url: str = ""                 # örn. redis://localhost:6379/0; boş = NullCache

    # ── Arama sıralaması (recency) ──────────────────────────────────────────
    # hybrid_search skoru relevance * decay_factor olarak hesaplanır (çarpımsal
    # — additive bonus skor tavanına (1.0) takılan tam eşleşmeleri etkilemiyordu).
    # decay_factor: bugün 1.0, window_days sonra decay_floor'a lineer iner.
    search_recency_decay_floor: float = 0.5
    search_recency_window_days: int = 30

    # ── Retention (eski haber temizliği) ────────────────────────────────────
    # ChromaDB'den eski vektörleri kaldırır (Postgres etkilenmez, reindex ile geri gelir).
    chroma_retention_days: int = 90      # 0 = kapalı
    # Postgres'ten KALICI silme — yıkıcı, varsayılan kapalı, bilinçli açılmalı.
    db_retention_days: int = 0           # 0 = kapalı
    retention_hour_utc: int = 4          # newsletter'dan (05:00 UTC) önce çalışır

    # ── Ham veri export (v1.16, Enterprise özelliği) ────────────────────────
    # Tek istekte döndürülen üst satır sınırı — runaway sorgudan/yanıttan korur.
    export_max_rows: int = 20000

    # ── WebSocket bağlantı tavanı (v1.18 güvenlik denetimi) ─────────────────
    # Tek bir Pro+ hesabın (veya toplamda tüm istemcilerin) sınırsız /ws/feed
    # bağlantısı açıp belleği/CPU'yu tüketmesini engeller.
    ws_max_connections_per_user: int = 5
    ws_max_total_connections: int = 500

    @property
    def admin_email_set(self) -> set[str]:
        """ADMIN_EMAILS değerini normalize edilmiş (küçük harf) set'e çevirir."""
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @model_validator(mode="after")
    def _reject_unsafe_production_config(self) -> "Settings":
        """`ENVIRONMENT=production` iken bilinen dev-only/zayıf değerlerle açılmayı reddeder.

        Güvenlik denetiminde bulunan dört madde tek yerde toplandı: unutulmuş
        varsayılan API_KEY, açık kalmış billing dev-mode simülasyonu, wildcard
        CORS ve HTTP üzerinden gönderilen session cookie. Dev/test ortamında
        `environment` varsayılanı "development" olduğu için bu kontrol hiç
        çalışmaz — sadece prod compose'un açıkça set ettiği ortamda devrededir.
        """
        if self.environment != "production":
            return self
        problems = []
        if self.api_key in ("", "dev-key-change-me"):
            problems.append("API_KEY varsayılan/boş bırakılmış")
        if self.billing_dev_mode:
            problems.append("BILLING_DEV_MODE açık kalmış (ücretsiz sınırsız yükseltme)")
        if self.cors_origins.strip() == "*":
            problems.append("CORS_ORIGINS wildcard (*) — gerçek domain'e sabitlenmeli")
        if not self.session_cookie_secure:
            problems.append("SESSION_COOKIE_SECURE=false — prod'da True olmalı")
        if problems:
            raise ValueError(
                "Production güvenlik kontrolü başarısız, uygulama başlatılmıyor: "
                + "; ".join(problems)
            )
        return self


settings = Settings()
