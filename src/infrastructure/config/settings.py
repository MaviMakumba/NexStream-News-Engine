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
        "CNN Türk,Sözcü,Habertürk,HT Spor,BBC Technology,BBC Sport"
    )

    # API Security
    api_key: str = "dev-key-change-me"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # CORS
    cors_origins: str = "*"


settings = Settings()
