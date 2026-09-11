-- v2.10 — /contact formundan gelen mesajlar artık DB'ye de yazılıyor (roadmap #26)
-- E-posta gönderimi spam'e düşse/gecikse/başarısız olsa bile mesaj admin
-- panelden (/admin/contact-messages) görülebilir kalsın diye.
CREATE TABLE IF NOT EXISTS contact_messages (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255),
    email       VARCHAR(255) NOT NULL,
    category    VARCHAR(32) NOT NULL,
    message     TEXT NOT NULL,
    language    VARCHAR(8) NOT NULL,
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_contact_messages_created_at ON contact_messages(created_at);
