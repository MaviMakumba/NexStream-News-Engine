-- v2.2: Kaydet / Sonra Oku (bookmarks) — rakip taraması sonrası quick-win paketi
-- (19 Ağu 2026, bkz. CLAUDE.md YOL HARİTASI). FK CASCADE yok — projenin genel
-- deseni, hesap silinirken satırlar UserRepository.delete_user'da elle temizlenir.
-- Dev ortamında SQLAlchemy create_all bu tabloyu otomatik oluşturur; bu script
-- mevcut production veritabanı içindir. Idempotent'tir.

CREATE TABLE IF NOT EXISTS saved_articles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_saved_articles_user_id ON saved_articles (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_saved_articles_user_article ON saved_articles (user_id, article_id);
