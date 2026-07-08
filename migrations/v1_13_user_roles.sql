-- v1.13: Yetki hiyerarşisi (user < moderator < admin) — v1.11'deki boolean
-- is_admin kolonunun yerini alır. Dev ortamında SQLAlchemy create_all mevcut
-- tabloları ALTER etmez, bu script hem dev'e elle hem prod'a esas olarak uygulanır.

-- 1. Yeni role kolonu, herkes için varsayılan 'user'.
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user';

-- 2. Mevcut is_admin=true kullanıcıları role='admin'e taşı (kolon varsa).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='is_admin') THEN
        UPDATE users SET role = 'admin' WHERE is_admin = TRUE;
    END IF;
END $$;

-- 3. Eski boolean kolonu kaldır — role tek doğruluk kaynağı.
ALTER TABLE users DROP COLUMN IF EXISTS is_admin;
