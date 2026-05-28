from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "nexstream"
    db_password: str = "nexstream"
    db_name: str = "nexstream_db"

    # Groq
    groq_api_key: str = ""

    # HuggingFace (Groq yedeği) — opsiyonel; boşsa fallback devre dışı
    huggingface_api_key: str = ""
    huggingface_model: str = "mistralai/Mistral-7B-Instruct-v0.3"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # Kafka
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_host: str = "kafka"
    kafka_port: int = 29092

    # Scheduler
    scrape_sources: str = (
        "TRT Haber,BBC Türkçe,Hürriyet,Hürriyet Spor,Sabah,"
        "CNN Türk,Sözcü,Habertürk,HT Spor,Anadolu Ajansı,AA Ekonomi,"
        "BBC Technology,BBC Sport,Guardian Tech,TechCrunch,Hacker News,The Verge"
    )

    # API Security
    api_key: str = "dev-key-change-me"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # CORS
    cors_origins: str = "*"

    # Email (newsletter / alerts)
    resend_api_key: str = ""          # if empty, falls back to console (log only)
    email_from: str = "NexStream <no-reply@nexstream.news>"
    newsletter_hour_utc: int = 5      # daily digest send time (05:00 UTC = 08:00 TR)


settings = Settings()
