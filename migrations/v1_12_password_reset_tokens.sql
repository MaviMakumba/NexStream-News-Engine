-- v1.12: Şifremi unuttum mekanizması
-- Dev ortamında SQLAlchemy create_all bu tabloyu otomatik oluşturur (yeni tablo);
-- bu script mevcut production veritabanları içindir. Idempotent'tir (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR(128) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_reset_tokens_user_id ON password_reset_tokens (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_reset_tokens_token ON password_reset_tokens (token);
