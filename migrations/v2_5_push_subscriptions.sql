-- v2.5 — Web push bildirim abonelikleri (roadmap #12)
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    endpoint    TEXT UNIQUE NOT NULL,
    p256dh      VARCHAR(255) NOT NULL,
    auth        VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_push_subscriptions_email ON push_subscriptions(email);
