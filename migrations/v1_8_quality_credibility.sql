-- v1.8.0 Migration: Add quality_score, credibility_score, corroboration_count columns
-- Run: docker exec -i nexstream_db psql -U postgres -d nexstream < migrations/v1_8_quality_credibility.sql

ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS quality_score DOUBLE PRECISION;
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS credibility_score DOUBLE PRECISION;
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS corroboration_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS ix_news_quality_score ON news_articles (quality_score);
