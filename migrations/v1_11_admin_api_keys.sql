-- v1.11: Rol tabanlı admin + kullanıcı başına API anahtarı
-- Dev ortamında SQLAlchemy create_all bu kolonları yeni tablolarda otomatik oluşturur;
-- bu script mevcut production veritabanları içindir. Idempotent'tir (IF NOT EXISTS).

-- Rol tabanlı admin: paylaşımlı API_KEY yerine kullanıcı bazlı yetkilendirme.
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- Kullanıcıya özel public API anahtarı (X-User-Key header'ı ile kullanılır).
ALTER TABLE users ADD COLUMN IF NOT EXISTS api_key VARCHAR(64);

-- API anahtarı ile hızlı kullanıcı çözümleme için unique index.
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_api_key ON users (api_key);

-- İlk admin ataması (opsiyonel — ADMIN_EMAILS env değişkeni de aynı işi görür):
-- UPDATE users SET is_admin = TRUE WHERE email = 'admin@example.com';
