-- v1.7 — Newsletter subscribers + user preferences
CREATE TABLE IF NOT EXISTS subscribers (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    keywords        JSONB NOT NULL DEFAULT '[]',
    preferred_sources JSONB NOT NULL DEFAULT '[]',
    preferred_topics  JSONB NOT NULL DEFAULT '[]',
    language        VARCHAR(10) NOT NULL DEFAULT 'TR',
    frequency       VARCHAR(20) NOT NULL DEFAULT 'daily',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_subscribers_email  ON subscribers(email);
CREATE INDEX IF NOT EXISTS ix_subscribers_active ON subscribers(is_active) WHERE is_active = TRUE;
