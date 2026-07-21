-- v1.15: E-posta doğrulama akışı (kayıtta gönderilen onay linki).
-- DNS/MX deliverability kontrolü (v1.14) gerçek bir domain + uydurma
-- kullanıcı adını (örn. rastgele123@gmail.com) yakalayamıyordu — bunun tek
-- gerçek çözümü budur. Gating YUMUŞAK: Free tier'da tam erişim korunur,
-- sadece ücretli kademeye yükseltme (billing checkout) doğrulama ister.
-- Dev ortamında SQLAlchemy create_all bu tabloyu/kolonu otomatik oluşturur;
-- bu script mevcut production veritabanları içindir. Idempotent'tir.

ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;

-- Zaten ücretli kademede olan kullanıcılar (dev-mode demo yükseltmeleri dahil)
-- bu migration'la geriye dönük kilitlenmesin.
UPDATE users SET email_verified = TRUE WHERE tier != 'free';

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR(128) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_email_verify_tokens_user_id ON email_verification_tokens (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_email_verify_tokens_token ON email_verification_tokens (token);
