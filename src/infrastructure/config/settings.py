"""Merkezi uygulama yapılandırması (Pydantic Settings).

Tüm ortam değişkenleri TEK noktadan okunur — `os.getenv()` kullanımı yasaktır.
Değerler `.env` dosyasından veya ortam değişkenlerinden gelir; alan adları
büyük/küçük harf duyarsız eşleşir (örn. `DB_HOST` → `db_host`).

Kullanım:
    from src.infrastructure.config.settings import settings
    settings.groq_api_key
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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

    # ── Kafka (scrape pipeline kuyruğu) ────────────────────────────────────
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_host: str = "kafka"
    kafka_port: int = 29092

    # ── Scheduler — taranacak kaynaklar (registry isimleriyle eşleşmeli) ───
    scrape_sources: str = (
        "TRT Haber,BBC Türkçe,Hürriyet,Hürriyet Spor,Sabah,"
        "CNN Türk,Sözcü,Habertürk,HT Spor,Anadolu Ajansı,AA Ekonomi,"
        "BBC Technology,BBC Sport,Guardian Tech,TechCrunch,Hacker News,The Verge"
    )

    # ── API güvenliği ──────────────────────────────────────────────────────
    # Paylaşımlı makine-makine anahtarı (X-API-Key). İnsan kullanıcılar için
    # v1.11'den itibaren rol tabanlı admin (users.is_admin) tercih edilir.
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
    newsletter_hour_utc: int = 5        # günlük digest saati (05:00 UTC = 08:00 TR)

    # ── Auth / Sessions ────────────────────────────────────────────────────
    session_ttl_days: int = 30

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

    @property
    def admin_email_set(self) -> set[str]:
        """ADMIN_EMAILS değerini normalize edilmiş (küçük harf) set'e çevirir."""
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


settings = Settings()
