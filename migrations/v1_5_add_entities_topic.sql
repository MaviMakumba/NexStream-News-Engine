-- v1.5.0 Migration: Add entities, topic, is_duplicate columns
-- Run: docker exec -i nexstream_db psql -U postgres -d nexstream < migrations/v1_5_add_entities_topic.sql

ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS entities JSONB;
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS topic VARCHAR(30);
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS ix_news_topic ON news_articles (topic);
